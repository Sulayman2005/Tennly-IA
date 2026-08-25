<?php

namespace App\State;

use ApiPlatform\Metadata\Operation;
use ApiPlatform\State\ProviderInterface;
use App\Dto\AdminDashboardSummary;
use App\Entity\Enum\BillingPeriod;
use App\Entity\Enum\MatchStatus;
use App\Entity\Enum\SubscriptionStatus;
use App\Entity\Prediction;
use App\Entity\Subscription;
use App\Entity\TennisMatch;
use App\Entity\User;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Calcule GET /api/admin/dashboard. Chaque agrégat vient d'une vraie requête
 * sur les données actuellement en base : aucune valeur n'est simulée.
 *
 * "Taux de réussite du modèle" = proportion de matchs *terminés* pour
 * lesquels le joueur favori de l'analyse IA a effectivement gagné (comparaison
 * Prediction::favoritePlayer vs TennisMatch::winner). Ce nombre grandira
 * naturellement avec l'historique une fois de vrais matchs à venir importés
 * (voir README "reste à faire" : calendrier de matchs à venir).
 *
 * @implements ProviderInterface<AdminDashboardSummary>
 */
final class AdminDashboardProvider implements ProviderInterface
{
    public function __construct(private readonly EntityManagerInterface $entityManager)
    {
    }

    public function provide(Operation $operation, array $uriVariables = [], array $context = []): AdminDashboardSummary
    {
        [$activeSubscriptionsCount, $subscribersByPlan, $mrrCents] = $this->computeSubscriberStats();
        [$modelAccuracyOverall, $modelAccuracyBySurface, $finishedWithPredictionCount] = $this->computeModelAccuracy();

        $predictionsCount = (int) $this->entityManager
            ->createQuery('SELECT COUNT(p) FROM '.Prediction::class.' p')
            ->getSingleScalarResult();

        $upcomingMatchesCount = (int) $this->entityManager
            ->getRepository(TennisMatch::class)
            ->createQueryBuilder('m')
            ->select('COUNT(m.id)')
            ->andWhere('m.status = :scheduled')
            ->setParameter('scheduled', MatchStatus::SCHEDULED)
            ->getQuery()
            ->getSingleScalarResult();

        [$totalUsersCount, $newUsersLast7Days] = $this->computeUserStats();
        $canceledSubscriptionsLast30Days = $this->computeChurn();
        $subscriptionsGrowth = $this->computeSubscriptionsGrowth();

        return new AdminDashboardSummary(
            activeSubscriptionsCount: $activeSubscriptionsCount,
            subscribersByPlan: $subscribersByPlan,
            mrrCents: $mrrCents,
            modelAccuracyOverall: $modelAccuracyOverall,
            modelAccuracyBySurface: $modelAccuracyBySurface,
            predictionsCount: $predictionsCount,
            finishedMatchesWithPredictionCount: $finishedWithPredictionCount,
            upcomingMatchesCount: $upcomingMatchesCount,
            totalUsersCount: $totalUsersCount,
            newUsersLast7Days: $newUsersLast7Days,
            canceledSubscriptionsLast30Days: $canceledSubscriptionsLast30Days,
            subscriptionsGrowth: $subscriptionsGrowth,
        );
    }

    /**
     * @return array{0: int, 1: int}
     */
    private function computeUserStats(): array
    {
        $totalUsersCount = (int) $this->entityManager
            ->createQuery('SELECT COUNT(u) FROM '.User::class.' u')
            ->getSingleScalarResult();

        $cutoff = (new \DateTimeImmutable('today'))->modify('-6 days');

        $newUsersLast7Days = (int) $this->entityManager
            ->getRepository(User::class)
            ->createQueryBuilder('u')
            ->select('COUNT(u.id)')
            ->andWhere('u.createdAt >= :cutoff')
            ->setParameter('cutoff', $cutoff, Types::DATETIME_IMMUTABLE)
            ->getQuery()
            ->getSingleScalarResult();

        return [$totalUsersCount, $newUsersLast7Days];
    }

    private function computeChurn(): int
    {
        $cutoff = (new \DateTimeImmutable('today'))->modify('-29 days');

        return (int) $this->entityManager
            ->getRepository(Subscription::class)
            ->createQueryBuilder('s')
            ->select('COUNT(s.id)')
            ->andWhere('s.canceledAt IS NOT NULL')
            ->andWhere('s.canceledAt >= :cutoff')
            ->setParameter('cutoff', $cutoff, Types::DATETIME_IMMUTABLE)
            ->getQuery()
            ->getSingleScalarResult();
    }

    /**
     * @return list<array{date: string, count: int}>
     */
    private function computeSubscriptionsGrowth(): array
    {
        $days = 14;
        $startOfWindow = (new \DateTimeImmutable('today'))->modify('-'.($days - 1).' days');

        /** @var Subscription[] $recentSubscriptions */
        $recentSubscriptions = $this->entityManager
            ->getRepository(Subscription::class)
            ->createQueryBuilder('s')
            ->andWhere('s.createdAt >= :start')
            ->setParameter('start', $startOfWindow, Types::DATETIME_IMMUTABLE)
            ->getQuery()
            ->getResult();

        // Un jour par clé, initialisé à 0 puis rempli avec les vrais abonnements —
        // jamais de trou dans la série (nécessaire pour un tracé continu), jamais
        // de jour inventé au-delà de la fenêtre réelle.
        $buckets = [];
        for ($i = 0; $i < $days; ++$i) {
            $buckets[$startOfWindow->modify("+{$i} days")->format('Y-m-d')] = 0;
        }

        foreach ($recentSubscriptions as $subscription) {
            $key = $subscription->getCreatedAt()->format('Y-m-d');
            if (isset($buckets[$key])) {
                ++$buckets[$key];
            }
        }

        $result = [];
        foreach ($buckets as $date => $count) {
            $result[] = ['date' => $date, 'count' => $count];
        }

        return $result;
    }

    /**
     * @return array{0: int, 1: list<array{code: string, name: string, count: int}>, 2: int}
     */
    private function computeSubscriberStats(): array
    {
        /** @var Subscription[] $activeSubscriptions */
        $activeSubscriptions = $this->entityManager
            ->getRepository(Subscription::class)
            ->createQueryBuilder('s')
            ->addSelect('plan')
            ->join('s.plan', 'plan')
            ->andWhere('s.status IN (:statuses)')
            ->setParameter('statuses', [SubscriptionStatus::ACTIVE, SubscriptionStatus::TRIALING])
            ->getQuery()
            ->getResult();

        $byPlan = [];
        $mrrCents = 0;

        foreach ($activeSubscriptions as $subscription) {
            $plan = $subscription->getPlan();
            $code = $plan->getCode();

            if (!isset($byPlan[$code])) {
                $byPlan[$code] = ['code' => $code, 'name' => $plan->getName(), 'count' => 0];
            }
            ++$byPlan[$code]['count'];

            $mrrCents += (int) round($this->monthlyEquivalentCents($plan->getPriceCents(), $plan->getBillingPeriod()));
        }

        return [count($activeSubscriptions), array_values($byPlan), $mrrCents];
    }

    /**
     * @return array{0: ?float, 1: list<array{surface: string, accuracy: float, sampleSize: int}>, 2: int}
     */
    private function computeModelAccuracy(): array
    {
        /** @var TennisMatch[] $finishedMatches */
        $finishedMatches = $this->entityManager
            ->getRepository(TennisMatch::class)
            ->createQueryBuilder('m')
            ->addSelect('prediction', 'favoritePlayer')
            ->join('m.prediction', 'prediction')
            ->join('prediction.favoritePlayer', 'favoritePlayer')
            ->andWhere('m.status = :finished')
            ->andWhere('m.winner IS NOT NULL')
            ->setParameter('finished', MatchStatus::FINISHED)
            ->getQuery()
            ->getResult();

        $correctBySurface = [];
        $totalBySurface = [];
        $correctOverall = 0;
        $totalOverall = 0;

        foreach ($finishedMatches as $match) {
            $prediction = $match->getPrediction();
            if (null === $prediction) {
                continue;
            }

            $surfaceKey = $match->getSurface()->value;
            $totalBySurface[$surfaceKey] = ($totalBySurface[$surfaceKey] ?? 0) + 1;
            ++$totalOverall;

            if ($prediction->getFavoritePlayer() === $match->getWinner()) {
                $correctBySurface[$surfaceKey] = ($correctBySurface[$surfaceKey] ?? 0) + 1;
                ++$correctOverall;
            }
        }

        $bySurface = [];
        foreach ($totalBySurface as $surfaceKey => $total) {
            $bySurface[] = [
                'surface' => $surfaceKey,
                'accuracy' => round((($correctBySurface[$surfaceKey] ?? 0) / $total) * 100, 1),
                'sampleSize' => $total,
            ];
        }

        $overall = $totalOverall > 0 ? round(($correctOverall / $totalOverall) * 100, 1) : null;

        return [$overall, $bySurface, $totalOverall];
    }

    private function monthlyEquivalentCents(int $priceCents, BillingPeriod $billingPeriod): float
    {
        return match ($billingPeriod) {
            BillingPeriod::MONTH => $priceCents,
            BillingPeriod::QUARTER => $priceCents / 3,
            BillingPeriod::YEAR => $priceCents / 12,
        };
    }
}

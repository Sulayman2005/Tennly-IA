<?php

namespace App\State;

use ApiPlatform\Metadata\Operation;
use ApiPlatform\State\ProviderInterface;
use App\Dto\HomeStatsSummary;
use App\Entity\Enum\MatchStatus;
use App\Entity\Prediction;
use App\Entity\TennisMatch;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Calcule GET /api/stats. Reprend volontairement le même calcul de "taux de
 * réussite" que AdminDashboardProvider::computeModelAccuracy() /
 * ModelReliabilityProvider (comparaison Prediction::favoritePlayer vs
 * TennisMatch::winner sur les matchs réellement terminés) plutôt que de le
 * factoriser dans un service partagé — même choix que ModelReliabilityProvider,
 * pour ne jamais risquer de régression sur les endpoints déjà en place en les
 * modifiant pour ce nouveau. Seule différence ici : ce chiffre est limité aux
 * 90 derniers jours (label "réussite sur 90 jours" de la page d'accueil).
 *
 * @implements ProviderInterface<HomeStatsSummary>
 */
final class HomeStatsProvider implements ProviderInterface
{
    public function __construct(private readonly EntityManagerInterface $entityManager)
    {
    }

    public function provide(Operation $operation, array $uriVariables = [], array $context = []): HomeStatsSummary
    {
        return new HomeStatsSummary(
            successRateLast90Days: $this->computeSuccessRateLast90Days(),
            analyzedMatchesCount: $this->countAnalyzedMatches(),
            averageValueEdgePercent: $this->computeAverageValueEdgePercent(),
            brierScore: $this->computeBrierScore(),
            yearsOfHistory: $this->computeYearsOfHistory(),
        );
    }

    private function computeSuccessRateLast90Days(): ?float
    {
        $cutoff = (new \DateTimeImmutable('today'))->modify('-89 days');

        /** @var TennisMatch[] $finishedMatches */
        $finishedMatches = $this->entityManager
            ->getRepository(TennisMatch::class)
            ->createQueryBuilder('m')
            ->addSelect('prediction')
            ->join('m.prediction', 'prediction')
            ->andWhere('m.status = :finished')
            ->andWhere('m.winner IS NOT NULL')
            ->andWhere('m.scheduledAt >= :cutoff')
            ->setParameter('finished', MatchStatus::FINISHED)
            ->setParameter('cutoff', $cutoff, Types::DATETIME_IMMUTABLE)
            ->getQuery()
            ->getResult();

        $total = count($finishedMatches);
        if (0 === $total) {
            return null;
        }

        $correct = 0;
        foreach ($finishedMatches as $match) {
            if ($match->getPrediction()?->getFavoritePlayer() === $match->getWinner()) {
                ++$correct;
            }
        }

        return round(($correct / $total) * 100, 1);
    }

    private function countAnalyzedMatches(): int
    {
        return (int) $this->entityManager
            ->createQuery('SELECT COUNT(p) FROM '.Prediction::class.' p')
            ->getSingleScalarResult();
    }

    /**
     * TOUJOURS null pour l'instant : Prediction::$valueEdge n'est encore
     * jamais renseigné par ml-service (voir le docstring de HomeStatsSummary).
     * Écrit comme une vraie requête plutôt qu'un `return null;` codé en dur,
     * pour que ce chiffre s'affiche automatiquement le jour où une source de
     * cotes de marché sera intégrée côté ml-service, sans toucher à ce fichier.
     */
    private function computeAverageValueEdgePercent(): ?float
    {
        $result = $this->entityManager
            ->getRepository(Prediction::class)
            ->createQueryBuilder('p')
            ->select('AVG(p.valueEdge) as avgEdge, COUNT(p.valueEdge) as sampleSize')
            ->andWhere('p.valueEdge IS NOT NULL')
            ->getQuery()
            ->getOneOrNullResult();

        if (null === $result || 0 === (int) $result['sampleSize']) {
            return null;
        }

        // Prediction::$valueEdge est stocké en fraction (0.041 = +4,1 %).
        return round(((float) $result['avgEdge']) * 100, 1);
    }

    private function computeBrierScore(): ?float
    {
        /** @var TennisMatch[] $finishedMatches */
        $finishedMatches = $this->entityManager
            ->getRepository(TennisMatch::class)
            ->createQueryBuilder('m')
            ->addSelect('prediction')
            ->join('m.prediction', 'prediction')
            ->andWhere('m.status = :finished')
            ->andWhere('m.winner IS NOT NULL')
            ->setParameter('finished', MatchStatus::FINISHED)
            ->getQuery()
            ->getResult();

        $total = count($finishedMatches);
        if (0 === $total) {
            return null;
        }

        // Brier score classique (binaire) : moyenne de (probabilité annoncée
        // pour le favori - résultat réel [1 si le favori a gagné, 0 sinon])².
        // Plus bas = modèle mieux calibré (0 = parfait, 1 = toujours faux).
        $sumSquaredError = 0.0;
        foreach ($finishedMatches as $match) {
            $prediction = $match->getPrediction();
            $outcome = $prediction?->getFavoritePlayer() === $match->getWinner() ? 1.0 : 0.0;
            $sumSquaredError += ($prediction->getProbabilityFavorite() - $outcome) ** 2;
        }

        return round($sumSquaredError / $total, 2);
    }

    /**
     * Nombre d'années couvertes par l'historique réel de matchs en base
     * (du plus ancien au plus récent scheduledAt), pas une constante codée
     * en dur — reflète ce qui a vraiment été importé, quelle que soit la
     * profondeur d'historique choisie côté ml-service.
     */
    private function computeYearsOfHistory(): ?float
    {
        $bounds = $this->entityManager
            ->getRepository(TennisMatch::class)
            ->createQueryBuilder('m')
            ->select('MIN(m.scheduledAt) as earliest, MAX(m.scheduledAt) as latest')
            ->getQuery()
            ->getOneOrNullResult();

        if (null === $bounds || null === $bounds['earliest'] || null === $bounds['latest']) {
            return null;
        }

        $earliest = new \DateTimeImmutable($bounds['earliest']);
        $latest = new \DateTimeImmutable($bounds['latest']);
        $days = $latest->diff($earliest)->days;

        return round($days / 365.25, 1);
    }
}

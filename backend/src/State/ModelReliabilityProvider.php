<?php

namespace App\State;

use ApiPlatform\Metadata\Operation;
use ApiPlatform\State\ProviderInterface;
use App\Dto\ModelReliabilitySummary;
use App\Entity\Enum\MatchStatus;
use App\Entity\Prediction;
use App\Entity\TennisMatch;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Calcule GET /api/model-reliability. Reprend volontairement le même calcul
 * de "taux de réussite" que AdminDashboardProvider::computeModelAccuracy()
 * plutôt que de le factoriser dans un service partagé : dupliquer ce calcul
 * simple évite de risquer une régression sur le tableau de bord admin déjà
 * en place en le modifiant pour cette nouvelle page.
 *
 * @implements ProviderInterface<ModelReliabilitySummary>
 */
final class ModelReliabilityProvider implements ProviderInterface
{
    private const CALIBRATION_BUCKETS = [
        ['min' => 0.5, 'max' => 0.6, 'label' => '50-60 %'],
        ['min' => 0.6, 'max' => 0.7, 'label' => '60-70 %'],
        ['min' => 0.7, 'max' => 0.8, 'label' => '70-80 %'],
        ['min' => 0.8, 'max' => 0.9, 'label' => '80-90 %'],
        ['min' => 0.9, 'max' => 1.01, 'label' => '90-100 %'],
    ];

    public function __construct(private readonly EntityManagerInterface $entityManager)
    {
    }

    public function provide(Operation $operation, array $uriVariables = [], array $context = []): ModelReliabilitySummary
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

        $bucketStats = [];
        foreach (self::CALIBRATION_BUCKETS as $bucket) {
            $bucketStats[$bucket['label']] = ['probaSum' => 0.0, 'correct' => 0, 'total' => 0];
        }

        foreach ($finishedMatches as $match) {
            $prediction = $match->getPrediction();
            if (null === $prediction) {
                continue;
            }

            $isCorrect = $prediction->getFavoritePlayer() === $match->getWinner();

            $surfaceKey = $match->getSurface()->value;
            $totalBySurface[$surfaceKey] = ($totalBySurface[$surfaceKey] ?? 0) + 1;
            ++$totalOverall;
            if ($isCorrect) {
                $correctBySurface[$surfaceKey] = ($correctBySurface[$surfaceKey] ?? 0) + 1;
                ++$correctOverall;
            }

            $probability = $prediction->getProbabilityFavorite();
            foreach (self::CALIBRATION_BUCKETS as $bucket) {
                if ($probability >= $bucket['min'] && $probability < $bucket['max']) {
                    $bucketStats[$bucket['label']]['probaSum'] += $probability;
                    ++$bucketStats[$bucket['label']]['total'];
                    if ($isCorrect) {
                        ++$bucketStats[$bucket['label']]['correct'];
                    }
                    break;
                }
            }
        }

        $accuracyBySurface = [];
        foreach ($totalBySurface as $surfaceKey => $total) {
            $accuracyBySurface[] = [
                'surface' => $surfaceKey,
                'accuracy' => round((($correctBySurface[$surfaceKey] ?? 0) / $total) * 100, 1),
                'sampleSize' => $total,
            ];
        }

        $calibrationBuckets = [];
        foreach (self::CALIBRATION_BUCKETS as $bucket) {
            $stats = $bucketStats[$bucket['label']];
            $sampleSize = $stats['total'];
            $calibrationBuckets[] = [
                'rangeLabel' => $bucket['label'],
                'rangeMin' => $bucket['min'],
                'rangeMax' => min($bucket['max'], 1.0),
                'predictedAvg' => $sampleSize > 0 ? round(($stats['probaSum'] / $sampleSize) * 100, 1) : null,
                'actualWinRate' => $sampleSize > 0 ? round(($stats['correct'] / $sampleSize) * 100, 1) : null,
                'sampleSize' => $sampleSize,
            ];
        }

        $overallAccuracy = $totalOverall > 0 ? round(($correctOverall / $totalOverall) * 100, 1) : null;

        $modelVersion = $this->entityManager
            ->createQuery('SELECT p.modelVersion FROM '.Prediction::class.' p ORDER BY p.computedAt DESC')
            ->setMaxResults(1)
            ->getOneOrNullResult();

        return new ModelReliabilitySummary(
            finishedMatchesWithPredictionCount: $totalOverall,
            overallAccuracy: $overallAccuracy,
            accuracyBySurface: $accuracyBySurface,
            calibrationBuckets: $calibrationBuckets,
            modelVersion: $modelVersion['modelVersion'] ?? null,
        );
    }
}
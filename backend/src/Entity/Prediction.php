<?php

namespace App\Entity;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use App\Entity\Enum\ConfidenceLevel;
use App\Repository\PredictionRepository;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Serializer\Annotation\Groups;

/**
 * Pronostic du modèle pour un match donné.
 *
 * Le découpage des groupes de sérialisation est ce qui implémente le paywall
 * décrit en section 3.2.1 du cahier des charges :
 *  - les champs tagués "match:read" sont l'aperçu gratuit, visibles quand la
 *    prédiction est embarquée dans la réponse GET /api/tennis_matches
 *    (tableau des matchs, accès public) ;
 *  - les champs tagués uniquement "prediction:read:detail" ne sortent que sur
 *    GET /api/predictions/{id}, une opération dont la sécurité exige un
 *    abonnement actif (fiche "player vs player", section 3.3).
 *
 * Écrite uniquement par le service data/ML (voir section 4.2.1 / 4.3),
 * jamais depuis l'application Symfony elle-même.
 */
#[ORM\Entity(repositoryClass: PredictionRepository::class)]
#[ORM\Table(name: 'prediction')]
#[ApiResource(
    operations: [
        new Get(
            security: "is_granted('ROLE_ADMIN') or (is_granted('ROLE_USER') and user.hasActiveSubscription())",
            securityMessage: "Analyse complète réservée aux abonnés — voir la popup paywall (section 3.2.1).",
            normalizationContext: ['groups' => ['match:read', 'prediction:read:detail']],
        ),
    ],
)]
class Prediction
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    #[Groups(['match:read'])]
    private ?int $id = null;

    #[ORM\OneToOne(targetEntity: TennisMatch::class, inversedBy: 'prediction')]
    #[ORM\JoinColumn(nullable: false)]
    private TennisMatch $match;

    #[ORM\ManyToOne(targetEntity: Player::class)]
    #[ORM\JoinColumn(nullable: false)]
    #[Groups(['match:read'])]
    private Player $favoritePlayer;

    /** Probabilité de victoire du favori, entre 0 et 1. */
    #[ORM\Column]
    #[Groups(['match:read'])]
    private float $probabilityFavorite;

    #[ORM\Column(enumType: ConfidenceLevel::class)]
    #[Groups(['match:read'])]
    private ConfidenceLevel $confidenceLevel;

    #[ORM\Column(length: 30)]
    #[Groups(['prediction:read:detail'])]
    private string $modelVersion;

    #[ORM\Column]
    #[Groups(['prediction:read:detail'])]
    private \DateTimeImmutable $computedAt;

    /**
     * Facteurs expliquant le pronostic, dans l'ordre d'impact (cahier des
     * charges section 3.3.4 "Pourquoi ce pronostic ?" et section 4.4.2).
     * Structure : liste de { label, favors: 'A'|'B', impactPoints: float, tone: 'ok'|'warn' }.
     */
    #[ORM\Column(type: Types::JSON)]
    #[Groups(['prediction:read:detail'])]
    private array $explanationFactors = [];

    /**
     * Profil comparatif à 6 axes pour le radar (section 3.3.2), normalisé sur 100.
     * Structure : { eloSurface: [a,b], forme: [a,b], service: [a,b], retour: [a,b], repos: [a,b], h2h: [a,b] }.
     */
    #[ORM\Column(type: Types::JSON)]
    #[Groups(['prediction:read:detail'])]
    private array $radarProfile = [];

    /**
     * Cote implicite du marché pour le favori, si disponible (section 4.2.1 :
     * agrégation des cotes de marché via API, pas de scraping de pronostiqueurs).
     */
    #[ORM\Column(nullable: true)]
    #[Groups(['prediction:read:detail'])]
    private ?float $marketOddsFavorite = null;

    /**
     * Écart entre la probabilité du modèle et la probabilité implicite de la
     * cote — sert d'indicateur de "value bet" (section 4.2.1 / 4.4.2).
     */
    #[ORM\Column(nullable: true)]
    #[Groups(['prediction:read:detail'])]
    private ?float $valueEdge = null;

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getMatch(): TennisMatch
    {
        return $this->match;
    }

    public function setMatch(TennisMatch $match): static
    {
        $this->match = $match;

        return $this;
    }

    public function getFavoritePlayer(): Player
    {
        return $this->favoritePlayer;
    }

    public function setFavoritePlayer(Player $favoritePlayer): static
    {
        $this->favoritePlayer = $favoritePlayer;

        return $this;
    }

    public function getProbabilityFavorite(): float
    {
        return $this->probabilityFavorite;
    }

    public function setProbabilityFavorite(float $probabilityFavorite): static
    {
        $this->probabilityFavorite = $probabilityFavorite;

        return $this;
    }

    public function getConfidenceLevel(): ConfidenceLevel
    {
        return $this->confidenceLevel;
    }

    public function setConfidenceLevel(ConfidenceLevel $confidenceLevel): static
    {
        $this->confidenceLevel = $confidenceLevel;

        return $this;
    }

    public function getModelVersion(): string
    {
        return $this->modelVersion;
    }

    public function setModelVersion(string $modelVersion): static
    {
        $this->modelVersion = $modelVersion;

        return $this;
    }

    public function getComputedAt(): \DateTimeImmutable
    {
        return $this->computedAt;
    }

    public function setComputedAt(\DateTimeImmutable $computedAt): static
    {
        $this->computedAt = $computedAt;

        return $this;
    }

    public function getExplanationFactors(): array
    {
        return $this->explanationFactors;
    }

    public function setExplanationFactors(array $explanationFactors): static
    {
        $this->explanationFactors = $explanationFactors;

        return $this;
    }

    public function getRadarProfile(): array
    {
        return $this->radarProfile;
    }

    public function setRadarProfile(array $radarProfile): static
    {
        $this->radarProfile = $radarProfile;

        return $this;
    }

    public function getMarketOddsFavorite(): ?float
    {
        return $this->marketOddsFavorite;
    }

    public function setMarketOddsFavorite(?float $marketOddsFavorite): static
    {
        $this->marketOddsFavorite = $marketOddsFavorite;

        return $this;
    }

    public function getValueEdge(): ?float
    {
        return $this->valueEdge;
    }

    public function setValueEdge(?float $valueEdge): static
    {
        $this->valueEdge = $valueEdge;

        return $this;
    }
}

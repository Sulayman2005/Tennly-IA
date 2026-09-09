<?php

namespace App\Entity;

use ApiPlatform\Doctrine\Orm\Filter\SearchFilter;
use ApiPlatform\Metadata\ApiFilter;
use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use ApiPlatform\Metadata\GetCollection;
use App\Repository\PlayerRepository;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Serializer\Annotation\Groups;

/**
 * Fiche joueur (cahier des charges section 3.4) : mise à jour automatiquement
 * après chaque match par le service data/ML (section 4.2.1 / 4.3), jamais
 * modifiée à la main depuis l'application Symfony.
 */
#[ORM\Entity(repositoryClass: PlayerRepository::class)]
#[ORM\Table(name: 'player')]
#[ApiResource(
    operations: [new GetCollection(), new Get()],
    normalizationContext: ['groups' => ['player:read']],
    order: ['eloOverall' => 'DESC'],
)]
// Nécessaire pour le comparateur de joueurs (frontend/src/views/ComparateurView.vue) :
// recherche d'un joueur par nom (partiel, insensible à l'ordre des mots côté
// frontend) via fullName=<recherche>.
#[ApiFilter(SearchFilter::class, properties: ['fullName' => 'partial'])]
class Player
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    #[Groups(['player:read', 'match:read'])]
    private ?int $id = null;

    #[ORM\Column(length: 150)]
    #[Groups(['player:read', 'match:read'])]
    private string $fullName;

    #[ORM\Column(length: 3, nullable: true)]
    #[Groups(['player:read', 'match:read'])]
    private ?string $countryCode = null;

    #[ORM\Column(nullable: true)]
    #[Groups(['player:read', 'match:read'])]
    private ?int $atpWtaRank = null;

    #[ORM\Column]
    #[Groups(['player:read'])]
    private float $eloOverall = 1500.0;

    #[ORM\Column]
    #[Groups(['player:read'])]
    private float $eloHard = 1500.0;

    #[ORM\Column]
    #[Groups(['player:read'])]
    private float $eloClay = 1500.0;

    #[ORM\Column]
    #[Groups(['player:read'])]
    private float $eloGrass = 1500.0;

    // Exposé côté API (Groups) pour le comparateur de joueurs — déjà utilisé
    // en interne par les scripts d'import (facteur "habitude du jeu face à
    // un gaucher/droitier"), jamais affiché côté frontend avant maintenant.
    #[ORM\Column(length: 1, nullable: true)]
    #[Groups(['player:read'])]
    private ?string $dominantHand = null;

    /**
     * Circuit du joueur : 'atp' ou 'wta' (voir ml-service/import_real_data.py
     * et import_upcoming_matches.py, qui traitent les deux circuits comme
     * deux univers Elo totalement séparés — un joueur ATP et une joueuse WTA
     * ne s'affrontent jamais). Défaut 'atp' pour rester valide sur les
     * joueurs déjà en base avant l'ajout de cette colonne.
     *
     * NOTE (28/08/2026) : cette propriété manquait entièrement de l'entité
     * alors que la colonne `tour` existait déjà en base (remplie par les
     * scripts ml-service via SQL direct) — résultat, Doctrine ignorait
     * complètement la colonne, l'API ne renvoyait jamais `tour`, et le badge
     * ATP/WTA du frontend retombait toujours sur "ATP" par défaut, quelle
     * que soit la vraie valeur en base. Voir aussi PlayerComparisonService.
     */
    #[ORM\Column(length: 3)]
    #[Groups(['player:read', 'match:read'])]
    private string $tour = 'atp';

    #[ORM\Column(nullable: true)]
    private ?\DateTimeImmutable $birthDate = null;

    /**
     * Identifiant du joueur dans les sources externes (Jeff Sackmann,
     * TennisMyLife — voir cahier des charges section 4.2), utilisé par le
     * service Python pour faire correspondre les lignes importées à ce joueur.
     */
    #[ORM\Column(length: 60, nullable: true, unique: true)]
    private ?string $externalRef = null;

    /**
     * URL de la photo officielle du joueur (Wikipedia/Wikimedia, licence
     * libre — voir ml-service/import_player_photos_wikipedia.py). Tant que
     * ce champ est vide pour un joueur donné, le frontend affiche l'avatar
     * générique (initiales + dégradé, voir utils/playerVisuals.js) —
     * jamais une image générée à sa place.
     *
     * Groups (09/09/2026) : ajout de 'match:read' en plus de 'player:read'.
     * TennisMatch::class normalise avec le seul groupe 'match:read'
     * (context propagé tel quel aux entités imbriquées playerA/playerB) —
     * sans ce groupe ici, photoUrl restait invisible sur GET
     * /api/tennis_matches malgré une valeur en base, alors qu'il était bien
     * renvoyé sur GET /api/players. Nécessaire pour afficher la photo dans
     * MatchCard.vue et la carte face-off de MatchDetailView.vue.
     */
    #[ORM\Column(length: 500, nullable: true)]
    #[Groups(['player:read', 'match:read'])]
    private ?string $photoUrl = null;

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getFullName(): string
    {
        return $this->fullName;
    }

    public function setFullName(string $fullName): static
    {
        $this->fullName = $fullName;

        return $this;
    }

    public function getCountryCode(): ?string
    {
        return $this->countryCode;
    }

    public function setCountryCode(?string $countryCode): static
    {
        $this->countryCode = $countryCode;

        return $this;
    }

    public function getAtpWtaRank(): ?int
    {
        return $this->atpWtaRank;
    }

    public function setAtpWtaRank(?int $atpWtaRank): static
    {
        $this->atpWtaRank = $atpWtaRank;

        return $this;
    }

    public function getEloOverall(): float
    {
        return $this->eloOverall;
    }

    public function setEloOverall(float $eloOverall): static
    {
        $this->eloOverall = $eloOverall;

        return $this;
    }

    public function getEloHard(): float
    {
        return $this->eloHard;
    }

    public function setEloHard(float $eloHard): static
    {
        $this->eloHard = $eloHard;

        return $this;
    }

    public function getEloClay(): float
    {
        return $this->eloClay;
    }

    public function setEloClay(float $eloClay): static
    {
        $this->eloClay = $eloClay;

        return $this;
    }

    public function getEloGrass(): float
    {
        return $this->eloGrass;
    }

    public function setEloGrass(float $eloGrass): static
    {
        $this->eloGrass = $eloGrass;

        return $this;
    }

    public function getDominantHand(): ?string
    {
        return $this->dominantHand;
    }

    public function setDominantHand(?string $dominantHand): static
    {
        $this->dominantHand = $dominantHand;

        return $this;
    }

    public function getBirthDate(): ?\DateTimeImmutable
    {
        return $this->birthDate;
    }

    public function setBirthDate(?\DateTimeImmutable $birthDate): static
    {
        $this->birthDate = $birthDate;

        return $this;
    }

    public function getExternalRef(): ?string
    {
        return $this->externalRef;
    }

    public function setExternalRef(?string $externalRef): static
    {
        $this->externalRef = $externalRef;

        return $this;
    }

    public function getPhotoUrl(): ?string
    {
        return $this->photoUrl;
    }

    public function setPhotoUrl(?string $photoUrl): static
    {
        $this->photoUrl = $photoUrl;

        return $this;
    }

    public function getTour(): string
    {
        return $this->tour;
    }

    public function setTour(string $tour): static
    {
        $this->tour = $tour;

        return $this;
    }
}
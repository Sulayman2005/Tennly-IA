<?php

namespace App\Entity;

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

    #[ORM\Column(length: 1, nullable: true)]
    private ?string $dominantHand = null;

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
     * Chemin/URL du visuel officiel du joueur, une fois les droits obtenus.
     * Tant que ce champ est vide, le frontend affiche le cadre photo
     * générique (voir prototype.html, .mc-photo) — jamais une image générée.
     */
    #[ORM\Column(length: 255, nullable: true)]
    #[Groups(['player:read'])]
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
}

<?php

namespace App\Entity;

use ApiPlatform\Metadata\ApiFilter;
use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use ApiPlatform\Metadata\GetCollection;
use ApiPlatform\Doctrine\Orm\Filter\DateFilter;
use ApiPlatform\Doctrine\Orm\Filter\OrderFilter;
use ApiPlatform\Doctrine\Orm\Filter\SearchFilter;
use App\Entity\Enum\MatchStatus;
use App\Entity\Enum\Surface;
use App\Repository\TennisMatchRepository;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Serializer\Annotation\Groups;

/**
 * Un match (nommé "TennisMatch" et non "Match" car `match` est un mot réservé
 * du langage PHP depuis la 8.0).
 *
 * Correspond au "Tableau des matchs" (cahier des charges section 3.2) : la
 * collection reste consultable librement en aperçu (nom des joueurs,
 * analyse du favori, niveau de confiance — voir Prediction), tandis que
 * l'item détaillé (fiche "player vs player", section 3.3) est réservé aux
 * abonnés, cf. la sécurité définie sur Prediction::class.
 */
#[ORM\Entity(repositoryClass: TennisMatchRepository::class)]
#[ORM\Table(name: 'tennis_match')]
#[ApiResource(
    operations: [new GetCollection(), new Get()],
    normalizationContext: ['groups' => ['match:read']],
    order: ['scheduledAt' => 'ASC'],
    paginationItemsPerPage: 20,
)]
#[ApiFilter(SearchFilter::class, properties: ['surface' => 'exact', 'status' => 'exact', 'tournamentName' => 'partial'])]
// Nécessaire pour le calendrier des matchs à venir (frontend/src/views/MatchesView.vue) :
// l'ordre par défaut de la ressource est ASC (le plus ancien d'abord), mais
// l'onglet "Résultats récents" a besoin du sens inverse (le plus récent
// d'abord) — order[scheduledAt]=desc — sans changer l'ordre par défaut
// pour tout le reste de l'API qui ne le demande pas explicitement.
#[ApiFilter(OrderFilter::class, properties: ['scheduledAt'])]
// Un match "scheduled" reste "scheduled" en base tant que personne n'a
// relancé l'import (voir ml-service/import_upcoming_matches.py) — sans
// filtre de date, un match programmé dont l'heure est déjà passée resterait
// affiché dans "À venir" jusqu'au prochain import. Ce filtre permet au
// frontend de demander scheduledAt[strictly_after]=<maintenant> pour ne
// garder que ce qui est VRAIMENT encore à venir au moment de l'affichage.
#[ApiFilter(DateFilter::class, properties: ['scheduledAt'])]
class TennisMatch
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    #[Groups(['match:read'])]
    private ?int $id = null;

    #[ORM\Column(length: 150)]
    #[Groups(['match:read'])]
    private string $tournamentName;

    #[ORM\Column(length: 60)]
    #[Groups(['match:read'])]
    private string $round;

    #[ORM\Column(enumType: Surface::class)]
    #[Groups(['match:read'])]
    private Surface $surface;

    #[ORM\Column]
    #[Groups(['match:read'])]
    private \DateTimeImmutable $scheduledAt;

    #[ORM\Column(enumType: MatchStatus::class)]
    #[Groups(['match:read'])]
    private MatchStatus $status;

    #[ORM\ManyToOne(targetEntity: Player::class)]
    #[ORM\JoinColumn(nullable: false)]
    #[Groups(['match:read'])]
    private Player $playerA;

    #[ORM\ManyToOne(targetEntity: Player::class)]
    #[ORM\JoinColumn(nullable: false)]
    #[Groups(['match:read'])]
    private Player $playerB;

    #[ORM\Column(length: 60, nullable: true)]
    #[Groups(['match:read'])]
    private ?string $scoreText = null;

    #[ORM\ManyToOne(targetEntity: Player::class)]
    #[ORM\JoinColumn(nullable: true)]
    #[Groups(['match:read'])]
    private ?Player $winner = null;

    #[ORM\OneToOne(targetEntity: Prediction::class, mappedBy: 'match', cascade: ['persist', 'remove'])]
    #[Groups(['match:read'])]
    private ?Prediction $prediction = null;

    /**
     * Identifiant du match dans une source externe (ex. "livetennisapi:12345"),
     * uniquement pour les matchs à venir importés par
     * ml-service/import_upcoming_matches.py — sert à savoir qu'un match a
     * déjà été importé lors d'une exécution précédente, pour ne jamais créer
     * de doublon quand le script tourne automatiquement chaque jour tant que
     * le match n'a pas encore eu lieu. Jamais exposé côté API (pas de Groups) :
     * c'est un détail d'implémentation du pipeline d'import, pas une donnée
     * utile au frontend.
     */
    #[ORM\Column(length: 60, nullable: true, unique: true)]
    private ?string $externalRef = null;

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getTournamentName(): string
    {
        return $this->tournamentName;
    }

    public function setTournamentName(string $tournamentName): static
    {
        $this->tournamentName = $tournamentName;

        return $this;
    }

    public function getRound(): string
    {
        return $this->round;
    }

    public function setRound(string $round): static
    {
        $this->round = $round;

        return $this;
    }

    public function getSurface(): Surface
    {
        return $this->surface;
    }

    public function setSurface(Surface $surface): static
    {
        $this->surface = $surface;

        return $this;
    }

    public function getScheduledAt(): \DateTimeImmutable
    {
        return $this->scheduledAt;
    }

    public function setScheduledAt(\DateTimeImmutable $scheduledAt): static
    {
        $this->scheduledAt = $scheduledAt;

        return $this;
    }

    public function getStatus(): MatchStatus
    {
        return $this->status;
    }

    public function setStatus(MatchStatus $status): static
    {
        $this->status = $status;

        return $this;
    }

    public function getPlayerA(): Player
    {
        return $this->playerA;
    }

    public function setPlayerA(Player $playerA): static
    {
        $this->playerA = $playerA;

        return $this;
    }

    public function getPlayerB(): Player
    {
        return $this->playerB;
    }

    public function setPlayerB(Player $playerB): static
    {
        $this->playerB = $playerB;

        return $this;
    }

    public function getScoreText(): ?string
    {
        return $this->scoreText;
    }

    public function setScoreText(?string $scoreText): static
    {
        $this->scoreText = $scoreText;

        return $this;
    }

    public function getWinner(): ?Player
    {
        return $this->winner;
    }

    public function setWinner(?Player $winner): static
    {
        $this->winner = $winner;

        return $this;
    }

    public function getPrediction(): ?Prediction
    {
        return $this->prediction;
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
}
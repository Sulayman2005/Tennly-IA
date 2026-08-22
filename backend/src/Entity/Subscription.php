<?php

namespace App\Entity;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use ApiPlatform\Metadata\GetCollection;
use App\Entity\Enum\SubscriptionStatus;
use App\Repository\SubscriptionRepository;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Serializer\Annotation\Groups;

/**
 * Abonnement d'un utilisateur à une formule (cahier des charges section 3.5 / 3.6).
 *
 * Créé uniquement à l'issue du parcours paywall -> connexion/inscription ->
 * paiement Stripe (jamais avant, voir User et section 3.9). Le statut suit le
 * cycle de vie standard Stripe (trialing -> active -> past_due -> canceled).
 */
#[ORM\Entity(repositoryClass: SubscriptionRepository::class)]
#[ORM\Table(name: 'subscription')]
#[ApiResource(
    operations: [
        new GetCollection(security: "is_granted('ROLE_USER')", securityMessage: "Connectez-vous pour voir vos abonnements."),
        new Get(security: "is_granted('ROLE_ADMIN') or object.getUser() == user"),
    ],
    normalizationContext: ['groups' => ['subscription:read']],
)]
class Subscription
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    #[Groups(['subscription:read'])]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: User::class, inversedBy: 'subscriptions')]
    #[ORM\JoinColumn(nullable: false)]
    private User $user;

    #[ORM\ManyToOne(targetEntity: Plan::class)]
    #[ORM\JoinColumn(nullable: false)]
    #[Groups(['subscription:read'])]
    private Plan $plan;

    #[ORM\Column(enumType: SubscriptionStatus::class)]
    #[Groups(['subscription:read'])]
    private SubscriptionStatus $status;

    #[ORM\Column(length: 120, nullable: true)]
    private ?string $stripeCustomerId = null;

    #[ORM\Column(length: 120, nullable: true)]
    private ?string $stripeSubscriptionId = null;

    #[ORM\Column(nullable: true)]
    #[Groups(['subscription:read'])]
    private ?\DateTimeImmutable $currentPeriodEnd = null;

    #[ORM\Column]
    #[Groups(['subscription:read'])]
    private \DateTimeImmutable $createdAt;

    #[ORM\Column(nullable: true)]
    #[Groups(['subscription:read'])]
    private ?\DateTimeImmutable $canceledAt = null;

    public function __construct()
    {
        $this->createdAt = new \DateTimeImmutable();
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getUser(): User
    {
        return $this->user;
    }

    public function setUser(User $user): static
    {
        $this->user = $user;

        return $this;
    }

    public function getPlan(): Plan
    {
        return $this->plan;
    }

    public function setPlan(Plan $plan): static
    {
        $this->plan = $plan;

        return $this;
    }

    public function getStatus(): SubscriptionStatus
    {
        return $this->status;
    }

    public function setStatus(SubscriptionStatus $status): static
    {
        $this->status = $status;

        return $this;
    }

    public function getStripeCustomerId(): ?string
    {
        return $this->stripeCustomerId;
    }

    public function setStripeCustomerId(?string $stripeCustomerId): static
    {
        $this->stripeCustomerId = $stripeCustomerId;

        return $this;
    }

    public function getStripeSubscriptionId(): ?string
    {
        return $this->stripeSubscriptionId;
    }

    public function setStripeSubscriptionId(?string $stripeSubscriptionId): static
    {
        $this->stripeSubscriptionId = $stripeSubscriptionId;

        return $this;
    }

    public function getCurrentPeriodEnd(): ?\DateTimeImmutable
    {
        return $this->currentPeriodEnd;
    }

    public function setCurrentPeriodEnd(?\DateTimeImmutable $currentPeriodEnd): static
    {
        $this->currentPeriodEnd = $currentPeriodEnd;

        return $this;
    }

    public function getCreatedAt(): \DateTimeImmutable
    {
        return $this->createdAt;
    }

    public function getCanceledAt(): ?\DateTimeImmutable
    {
        return $this->canceledAt;
    }

    public function setCanceledAt(?\DateTimeImmutable $canceledAt): static
    {
        $this->canceledAt = $canceledAt;

        return $this;
    }

    public function isActive(): bool
    {
        return in_array($this->status, [SubscriptionStatus::ACTIVE, SubscriptionStatus::TRIALING], true);
    }
}

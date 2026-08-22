<?php

namespace App\Entity;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\GetCollection;
use App\Entity\Enum\BillingPeriod;
use App\Repository\PlanRepository;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Serializer\Annotation\Groups;

/**
 * Formule tarifaire (cahier des charges section 3.2.1 / 3.5) :
 * Classique (mensuel), VIP (trimestriel), VIP annuel.
 *
 * Le "code" (classique|vip|vip-annuel) correspond exactement à la valeur du
 * paramètre ?plan= utilisé par la maquette connexion.html pour préremplir le
 * bandeau de rappel de formule (voir section 12.1.5 du cahier des charges).
 */
#[ORM\Entity(repositoryClass: PlanRepository::class)]
#[ORM\Table(name: 'plan')]
#[ApiResource(
    operations: [new GetCollection()],
    normalizationContext: ['groups' => ['plan:read']],
)]
class Plan
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    #[Groups(['plan:read'])]
    private ?int $id = null;

    #[ORM\Column(length: 30, unique: true)]
    #[Groups(['plan:read'])]
    private string $code;

    #[ORM\Column(length: 100)]
    #[Groups(['plan:read'])]
    private string $name;

    #[ORM\Column]
    #[Groups(['plan:read'])]
    private int $priceCents;

    #[ORM\Column(length: 3)]
    #[Groups(['plan:read'])]
    private string $currency = 'EUR';

    #[ORM\Column(enumType: BillingPeriod::class)]
    #[Groups(['plan:read'])]
    private BillingPeriod $billingPeriod;

    #[ORM\Column(length: 120, nullable: true)]
    private ?string $stripePriceId = null;

    #[ORM\Column]
    #[Groups(['plan:read'])]
    private bool $active = true;

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getCode(): string
    {
        return $this->code;
    }

    public function setCode(string $code): static
    {
        $this->code = $code;

        return $this;
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function setName(string $name): static
    {
        $this->name = $name;

        return $this;
    }

    public function getPriceCents(): int
    {
        return $this->priceCents;
    }

    public function setPriceCents(int $priceCents): static
    {
        $this->priceCents = $priceCents;

        return $this;
    }

    public function getCurrency(): string
    {
        return $this->currency;
    }

    public function setCurrency(string $currency): static
    {
        $this->currency = $currency;

        return $this;
    }

    public function getBillingPeriod(): BillingPeriod
    {
        return $this->billingPeriod;
    }

    public function setBillingPeriod(BillingPeriod $billingPeriod): static
    {
        $this->billingPeriod = $billingPeriod;

        return $this;
    }

    public function getStripePriceId(): ?string
    {
        return $this->stripePriceId;
    }

    public function setStripePriceId(?string $stripePriceId): static
    {
        $this->stripePriceId = $stripePriceId;

        return $this;
    }

    public function isActive(): bool
    {
        return $this->active;
    }

    public function setActive(bool $active): static
    {
        $this->active = $active;

        return $this;
    }
}

<?php

namespace App\Entity;

use ApiPlatform\Metadata\ApiResource;
use ApiPlatform\Metadata\Get;
use ApiPlatform\Metadata\GetCollection;
use ApiPlatform\Metadata\Post;
use App\Repository\UserRepository;
use App\State\CurrentUserProvider;
use App\State\UserRegistrationProcessor;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;
use Symfony\Component\Serializer\Annotation\Groups;
use Symfony\Component\Uid\Uuid;
use Symfony\Component\Validator\Constraints as Assert;
use Symfony\Component\Security\Core\User\PasswordAuthenticatedUserInterface;
use Symfony\Component\Security\Core\User\UserInterface;

/**
 * Compte utilisateur.
 *
 * Rappel produit (cahier des charges section 3.9) : la création d'un compte
 * n'est jamais un geste "gratuit" isolé côté frontend — elle n'est déclenchée
 * que par le clic sur une formule dans la popup paywall (section 3.2.1). Un
 * compte créé est immédiatement suivi de la création d'un Subscription en
 * statut "trialing"/"active" une fois le paiement Stripe confirmé.
 */
#[ORM\Entity(repositoryClass: UserRepository::class)]
#[ORM\Table(name: 'app_user')]
#[ORM\UniqueConstraint(name: 'uniq_user_email', fields: ['email'])]
#[ApiResource(
    operations: [
        new GetCollection(security: "is_granted('ROLE_ADMIN')"),
        new Get(security: "is_granted('ROLE_ADMIN') or object == user"),
        // GET /api/me : ce que le frontend appelle après connexion pour savoir
        // qui est l'utilisateur courant et s'il a un abonnement actif (voir
        // hasActiveSubscription() plus bas et frontend/src/stores/auth.js).
        // Un uriTemplate fixe (pas d'{id}) + un provider dédié qui renvoie
        // toujours l'utilisateur de la requête en cours, jamais un id arbitraire.
        new Get(
            uriTemplate: '/me',
            security: "is_granted('ROLE_USER')",
            provider: CurrentUserProvider::class,
        ),
        new Post(
            uriTemplate: '/register',
            processor: UserRegistrationProcessor::class,
            security: null,
            validationContext: ['groups' => ['user:write:register']],
        ),
    ],
    normalizationContext: ['groups' => ['user:read']],
    denormalizationContext: ['groups' => ['user:write:register']],
)]
class User implements UserInterface, PasswordAuthenticatedUserInterface
{
    #[ORM\Id]
    #[ORM\Column(type: Types::GUID, unique: true)]
    #[Groups(['user:read'])]
    private string $id;

    #[ORM\Column(length: 180)]
    #[Assert\NotBlank(groups: ['user:write:register'])]
    #[Assert\Email(groups: ['user:write:register'])]
    #[Groups(['user:read', 'user:write:register'])]
    private string $email;

    /** @var list<string> */
    #[ORM\Column]
    #[Groups(['user:read'])]
    private array $roles = [];

    #[ORM\Column]
    private string $password;

    /**
     * Mot de passe en clair, jamais persisté : uniquement utilisé le temps du
     * hachage dans UserRegistrationProcessor. @see UserRegistrationProcessor
     */
    #[Assert\NotBlank(groups: ['user:write:register'])]
    #[Assert\Length(min: 8, groups: ['user:write:register'])]
    #[Groups(['user:write:register'])]
    private ?string $plainPassword = null;

    #[ORM\Column(length: 100)]
    #[Assert\NotBlank(groups: ['user:write:register'])]
    #[Groups(['user:read', 'user:write:register'])]
    private string $firstName;

    #[ORM\Column(length: 100)]
    #[Assert\NotBlank(groups: ['user:write:register'])]
    #[Groups(['user:read', 'user:write:register'])]
    private string $lastName;

    #[ORM\Column]
    #[Groups(['user:read'])]
    private \DateTimeImmutable $createdAt;

    /**
     * Code de la formule choisie dans la popup paywall (classique|vip|vip-annuel,
     * voir connexion.html?plan=... et cahier des charges section 3.9). Champ
     * transitoire, non persisté : uniquement lu par UserRegistrationProcessor
     * pour démarrer la session de paiement Stripe juste après la création du compte.
     */
    #[Groups(['user:write:register'])]
    private ?string $planCode = null;

    /**
     * URL de la session Stripe Checkout à ouvrir côté frontend juste après
     * l'inscription (bouton "Continuer vers le paiement"). Champ transitoire,
     * rempli par UserRegistrationProcessor, jamais persisté.
     */
    #[Groups(['user:read'])]
    private ?string $checkoutUrl = null;

    /** @var Collection<int, Subscription> */
    #[ORM\OneToMany(targetEntity: Subscription::class, mappedBy: 'user', orphanRemoval: true)]
    private Collection $subscriptions;

    public function __construct()
    {
        $this->id = Uuid::v7()->toRfc4122();
        $this->createdAt = new \DateTimeImmutable();
        $this->subscriptions = new ArrayCollection();
    }

    public function getId(): string
    {
        return $this->id;
    }

    public function getEmail(): string
    {
        return $this->email;
    }

    public function setEmail(string $email): static
    {
        $this->email = $email;

        return $this;
    }

    public function getUserIdentifier(): string
    {
        return $this->email;
    }

    /** @return list<string> */
    public function getRoles(): array
    {
        $roles = $this->roles;
        $roles[] = 'ROLE_USER';

        return array_values(array_unique($roles));
    }

    /** @param list<string> $roles */
    public function setRoles(array $roles): static
    {
        $this->roles = $roles;

        return $this;
    }

    public function getPassword(): string
    {
        return $this->password;
    }

    public function setPassword(string $password): static
    {
        $this->password = $password;

        return $this;
    }

    public function getPlainPassword(): ?string
    {
        return $this->plainPassword;
    }

    public function setPlainPassword(?string $plainPassword): static
    {
        $this->plainPassword = $plainPassword;

        return $this;
    }

    public function eraseCredentials(): void
    {
        $this->plainPassword = null;
    }

    public function getFirstName(): string
    {
        return $this->firstName;
    }

    public function setFirstName(string $firstName): static
    {
        $this->firstName = $firstName;

        return $this;
    }

    public function getLastName(): string
    {
        return $this->lastName;
    }

    public function setLastName(string $lastName): static
    {
        $this->lastName = $lastName;

        return $this;
    }

    public function getCreatedAt(): \DateTimeImmutable
    {
        return $this->createdAt;
    }

    /** @return Collection<int, Subscription> */
    public function getSubscriptions(): Collection
    {
        return $this->subscriptions;
    }

    public function getPlanCode(): ?string
    {
        return $this->planCode;
    }

    public function setPlanCode(?string $planCode): static
    {
        $this->planCode = $planCode;

        return $this;
    }

    public function getCheckoutUrl(): ?string
    {
        return $this->checkoutUrl;
    }

    public function setCheckoutUrl(?string $checkoutUrl): static
    {
        $this->checkoutUrl = $checkoutUrl;

        return $this;
    }

    /**
     * Utilisé dans les expressions de sécurité API Platform pour distinguer
     * l'aperçu gratuit (section 3.2) de la fiche détaillée réservée aux
     * abonnés (section 3.3, derrière le paywall décrit en 3.2.1).
     *
     * Également exposé en lecture (groupe "user:read") sur GET /api/me : c'est
     * ce que le frontend (stores/auth.js) lit pour savoir s'il doit afficher
     * la popup paywall ou le contenu complet, sans jamais faire confiance à un
     * état local non vérifié côté serveur.
     */
    #[Groups(['user:read'])]
    public function hasActiveSubscription(): bool
    {
        foreach ($this->subscriptions as $subscription) {
            if ($subscription->isActive()) {
                return true;
            }
        }

        return false;
    }

    public function hasVipAccess(): bool
    {
        foreach ($this->subscriptions as $subscription) {
            if ($subscription->isActive() && $subscription->getPlan()->getCode() !== 'classique') {
                return true;
            }
        }

        return false;
    }
}

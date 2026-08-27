<?php

namespace App\Service;

use App\Entity\Plan;
use App\Entity\User;
use Stripe\Checkout\Session;
use Stripe\StripeClient;

/**
 * Encapsule la création d'une session Stripe Checkout pour un couple
 * (utilisateur, formule) — cahier des charges section 3.6 "Paiement et abonnement".
 *
 * Déclenchée depuis CheckoutSessionController, lui-même appelé au moment où
 * un utilisateur DÉJÀ connecté choisit une formule depuis la popup paywall
 * d'un match précis (voir PaywallModal.vue) — plus jamais automatiquement à
 * l'inscription (voir UserRegistrationProcessor, qui ne fait plus que créer
 * le compte). `$returnPath` est le chemin du match qui a déclenché le
 * paiement, pour renvoyer l'utilisateur exactement là où il voulait aller une
 * fois le paiement confirmé plutôt que sur une page d'accueil générique.
 */
class StripeCheckoutService
{
    private StripeClient $stripe;

    public function __construct(
        string $stripeSecretKey,
        private readonly string $frontendBaseUrl,
    ) {
        $this->stripe = new StripeClient($stripeSecretKey);
    }

    public function createCheckoutSessionUrl(
        User $user,
        Plan $plan,
        string $returnPath = '/matchs',
        ?\DateTimeImmutable $withdrawalWaiverAcceptedAt = null,
    ): string {
        $base = rtrim($this->frontendBaseUrl, '/').$returnPath;
        $separator = str_contains($returnPath, '?') ? '&' : '?';

        // Preuve de la renonciation au droit de rétractation : enregistrée à la
        // fois sur la session ET sur l'abonnement Stripe (subscription_data),
        // pour rester consultable dans le temps, pas seulement le temps d'une
        // session Checkout éphémère.
        $waiverMetadata = null !== $withdrawalWaiverAcceptedAt ? [
            'withdrawal_waiver_accepted' => 'true',
            'withdrawal_waiver_accepted_at' => $withdrawalWaiverAcceptedAt->format(DATE_ATOM),
        ] : [];

        /** @var Session $session */
        $session = $this->stripe->checkout->sessions->create([
            'mode' => 'subscription',
            'customer_email' => $user->getEmail(),
            'client_reference_id' => $user->getId(),
            'line_items' => [[
                'price' => $plan->getStripePriceId(),
                'quantity' => 1,
            ]],
            'metadata' => [
                'plan_code' => $plan->getCode(),
                ...$waiverMetadata,
            ],
            'subscription_data' => [
                'metadata' => $waiverMetadata,
            ],
            'success_url' => $base.$separator.'paiement=reussi&session_id={CHECKOUT_SESSION_ID}',
            'cancel_url' => $base,
        ]);

        return $session->url;
    }
}
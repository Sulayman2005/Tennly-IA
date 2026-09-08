<?php

namespace App\Service;

use App\Entity\Plan;
use App\Entity\User;
use Stripe\Checkout\Session;
use Stripe\StripeClient;

/**
 * Encapsule la création (et désormais la relecture) d'une session Stripe
 * Checkout pour une formule — cahier des charges section 3.6 "Paiement et
 * abonnement".
 *
 * Déclenchée depuis CheckoutSessionController au moment où un utilisateur
 * choisit une formule depuis la popup paywall d'un match précis (voir
 * PaywallModal.vue). Décision produit du 03/09/2026 : le paiement se
 * déclenche désormais AVANT toute connexion — `$user` peut donc être `null`
 * (visiteur pas encore connecté). Dans ce cas Stripe Checkout collecte
 * lui-même l'email du payeur, et la création du compte / le rattachement de
 * l'abonnement se fait après coup, une fois le paiement confirmé (voir
 * CheckoutSessionStatusController et CheckoutSessionLinkController). Un
 * utilisateur déjà connecté garde exactement l'ancien comportement
 * (customer_email / client_reference_id préremplis, activation via le
 * webhook StripeWebhookController).
 *
 * `$returnPath` est le chemin du match qui a déclenché le paiement, pour
 * renvoyer l'utilisateur exactement là où il voulait aller une fois le
 * paiement confirmé plutôt que sur une page d'accueil générique.
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
        ?User $user,
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

        $params = [
            'mode' => 'subscription',
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
        ];

        // Utilisateur déjà connecté au moment du clic : on préremplit son
        // email et on garde le lien direct client_reference_id -> User pour
        // que le webhook active l'abonnement sans étape supplémentaire (voir
        // StripeWebhookController). Visiteur anonyme : on laisse Stripe
        // Checkout demander lui-même l'email, il n'y a pas encore de compte
        // auquel le relier.
        if (null !== $user) {
            $params['customer_email'] = $user->getEmail();
            $params['client_reference_id'] = $user->getId();
        }

        /** @var Session $session */
        $session = $this->stripe->checkout->sessions->create($params);

        return $session->url;
    }

    /**
     * Relit une session Stripe Checkout après coup (voir
     * CheckoutSessionStatusController / CheckoutSessionLinkController) —
     * utilisé uniquement pour le parcours "paiement avant connexion" : on ne
     * fait jamais confiance à ce que le frontend affirme sur un paiement,
     * uniquement à ce que Stripe renvoie ici, server-side.
     */
    public function retrieveSession(string $sessionId): Session
    {
        return $this->stripe->checkout->sessions->retrieve($sessionId);
    }
}

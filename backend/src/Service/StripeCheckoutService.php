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
 * Déclenchée uniquement juste après l'inscription initiée depuis la popup
 * paywall (voir UserRegistrationProcessor et section 3.9), jamais à un autre
 * moment : il n'y a pas de tunnel d'abonnement indépendant de l'inscription.
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

    public function createCheckoutSessionUrl(User $user, Plan $plan): string
    {
        /** @var Session $session */
        $session = $this->stripe->checkout->sessions->create([
            'mode' => 'subscription',
            'customer_email' => $user->getEmail(),
            'client_reference_id' => $user->getId(),
            'line_items' => [[
                'price' => $plan->getStripePriceId(),
                'quantity' => 1,
            ]],
            // Le webhook (StripeWebhookController) n'a accès qu'au payload de
            // l'événement Stripe, jamais à la requête HTTP d'origine : la
            // formule choisie doit donc voyager dans les métadonnées de la
            // session plutôt que dans un paramètre de requête inexistant à ce
            // stade (voir cahier des charges section 3.6).
            'metadata' => [
                'plan_code' => $plan->getCode(),
            ],
            'success_url' => rtrim($this->frontendBaseUrl, '/').'/compte/bienvenue?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url' => rtrim($this->frontendBaseUrl, '/').'/matchs',
        ]);

        return $session->url;
    }
}

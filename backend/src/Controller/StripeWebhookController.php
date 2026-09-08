<?php

namespace App\Controller;

use App\Entity\Enum\SubscriptionStatus;
use App\Entity\Subscription;
use App\Repository\PlanRepository;
use App\Repository\UserRepository;
use Doctrine\ORM\EntityManagerInterface;
use Stripe\Webhook;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * Reçoit les événements Stripe (cahier des charges section 3.6). Concrétise
 * l'abonnement (statut "active") une fois le paiement confirmé côté Stripe —
 * c'est la toute dernière étape du parcours paywall -> inscription -> paiement
 * décrit en section 3.9.
 */
final class StripeWebhookController
{
    public function __construct(
        private readonly EntityManagerInterface $entityManager,
        private readonly UserRepository $userRepository,
        private readonly PlanRepository $planRepository,
        private readonly string $stripeWebhookSecret,
    ) {
    }

    #[Route('/api/stripe/webhook', name: 'stripe_webhook', methods: ['POST'])]
    public function __invoke(Request $request): Response
    {
        try {
            $event = Webhook::constructEvent(
                $request->getContent(),
                (string) $request->headers->get('Stripe-Signature'),
                $this->stripeWebhookSecret,
            );
        } catch (\Exception) {
            return new JsonResponse(['error' => 'Signature invalide'], Response::HTTP_BAD_REQUEST);
        }

        if ('checkout.session.completed' === $event->type) {
            $session = $event->data->object;
            $user = null !== $session->client_reference_id
                ? $this->userRepository->find($session->client_reference_id)
                : null;

            if (null !== $user) {
                $subscription = new Subscription();
                $subscription->setUser($user);
                // Le code de la formule voyage dans les métadonnées de la session
                // Stripe (voir StripeCheckoutService::createCheckoutSessionUrl) —
                // ce webhook ne voit que le payload de l'événement Stripe, jamais
                // la requête HTTP d'origine, donc un paramètre de requête ?plan=
                // n'existerait de toute façon jamais ici.
                $planCode = $session->metadata->plan_code ?? 'classique';
                $plan = $this->planRepository->findOneByCode($planCode);
                if (null !== $plan) {
                    $subscription->setPlan($plan);
                }
                $subscription->setStatus(SubscriptionStatus::ACTIVE);
                $subscription->setStripeCustomerId($session->customer);
                $subscription->setStripeSubscriptionId($session->subscription);

                $this->entityManager->persist($subscription);
                $this->entityManager->flush();
            }
        }

        return new JsonResponse(['received' => true]);
    }
}

<?php

namespace App\Controller;

use App\Entity\Enum\SubscriptionStatus;
use App\Entity\Subscription;
use App\Entity\User;
use App\Repository\PlanRepository;
use App\Repository\SubscriptionRepository;
use App\Service\StripeCheckoutService;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;

/**
 * POST /api/checkout-sessions/{sessionId}/link — relie un paiement Stripe
 * déjà confirmé au compte qui vient tout juste de se connecter ou de
 * s'inscrire (`#[IsGranted('ROLE_USER')]` : il faut donc être authentifié
 * pour l'appeler, ce qui est toujours le cas juste après
 * auth.login()/auth.register() côté frontend, voir PostPaymentModal.vue).
 *
 * Complète, pour le parcours "paiement avant connexion" (décision produit du
 * 03/09/2026), ce que StripeWebhookController fait déjà pour un utilisateur
 * qui payait en étant déjà connecté : créer l'abonnement une fois le
 * paiement confirmé. On revérifie ici server-side, auprès de Stripe, que le
 * paiement est bien confirmé ET que l'email utilisé sur Stripe correspond
 * exactement à celui du compte courant — jamais uniquement sur la foi de ce
 * qu'envoie le frontend — pour qu'un utilisateur ne puisse jamais relier à
 * son propre compte le paiement de quelqu'un d'autre.
 */
final class CheckoutSessionLinkController extends AbstractController
{
    public function __construct(
        private readonly StripeCheckoutService $stripeCheckoutService,
        private readonly PlanRepository $planRepository,
        private readonly SubscriptionRepository $subscriptionRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
    }

    #[Route('/api/checkout-sessions/{sessionId}/link', name: 'checkout_session_link', methods: ['POST'])]
    #[IsGranted('ROLE_USER')]
    public function __invoke(string $sessionId): JsonResponse
    {
        try {
            $session = $this->stripeCheckoutService->retrieveSession($sessionId);
        } catch (\Exception) {
            return $this->json(['detail' => 'Session de paiement introuvable.'], Response::HTTP_NOT_FOUND);
        }

        if ('paid' !== $session->payment_status) {
            return $this->json(['detail' => "Ce paiement n'est pas confirmé."], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        /** @var User $user */
        $user = $this->getUser();

        $sessionEmail = $session->customer_details->email ?? $session->customer_email ?? null;
        if (null === $sessionEmail || strtolower($sessionEmail) !== strtolower($user->getEmail())) {
            return $this->json(['detail' => 'Ce paiement est associé à une autre adresse email.'], Response::HTTP_FORBIDDEN);
        }

        // Idempotence : un rechargement de page (ou un double clic) ne doit
        // jamais créer un doublon d'abonnement pour la même session Stripe —
        // que ce soit ce endpoint ou le webhook (StripeWebhookController) qui
        // l'ait déjà créé entre-temps.
        $existing = null !== $session->subscription
            ? $this->subscriptionRepository->findOneBy(['stripeSubscriptionId' => $session->subscription])
            : null;
        if (null !== $existing) {
            return $this->json(['linked' => true]);
        }

        $planCode = $session->metadata->plan_code ?? 'classique';
        $plan = $this->planRepository->findOneByCode($planCode);

        $subscription = new Subscription();
        $subscription->setUser($user);
        if (null !== $plan) {
            $subscription->setPlan($plan);
        }
        $subscription->setStatus(SubscriptionStatus::ACTIVE);
        $subscription->setStripeCustomerId($session->customer);
        $subscription->setStripeSubscriptionId($session->subscription);

        $this->entityManager->persist($subscription);
        $this->entityManager->flush();

        return $this->json(['linked' => true]);
    }
}

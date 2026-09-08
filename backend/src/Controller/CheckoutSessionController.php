<?php

namespace App\Controller;

use App\Entity\User;
use App\Repository\PlanRepository;
use App\Service\StripeCheckoutService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * POST /api/checkout-sessions — démarre un paiement Stripe pour la formule
 * choisie depuis la popup paywall d'un match (voir PaywallModal.vue).
 *
 * Décision produit du 03/09/2026 : le paiement se déclenche désormais
 * immédiatement au clic sur une formule, QUE l'utilisateur soit déjà
 * connecté ou non — donc plus de `#[IsGranted('ROLE_USER')]` ici. Un compte
 * déjà connecté garde l'ancien comportement (activation via le webhook,
 * StripeWebhookController). Un visiteur anonyme paie d'abord ; le compte est
 * créé (ou l'utilisateur se connecte, si l'email a déjà un compte) juste
 * après un retour de paiement confirmé, voir CheckoutSessionStatusController
 * et CheckoutSessionLinkController — jamais avant.
 */
#[Route('/api/checkout-sessions', name: 'checkout_session_create', methods: ['POST'])]
final class CheckoutSessionController extends AbstractController
{
    public function __construct(
        private readonly PlanRepository $planRepository,
        private readonly StripeCheckoutService $stripeCheckoutService,
    ) {
    }

    public function __invoke(Request $request): JsonResponse
    {
        $payload = json_decode($request->getContent(), true) ?? [];
        $planCode = is_string($payload['planCode'] ?? null) ? $payload['planCode'] : null;
        $redirectPath = $payload['redirectPath'] ?? null;

        $plan = $planCode ? $this->planRepository->findOneByCode($planCode) : null;
        if (null === $plan) {
            return $this->json(['detail' => 'Formule inconnue.'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }
        // CGV article 4 : renonciation obligatoire au droit de rétractation pour
        // un accès immédiat (art. L221-28 13° du Code de la consommation). On
        // revalide ici même si le frontend a déjà la case à cocher : un appel
        // direct à cette API ne doit jamais pouvoir la contourner — y compris
        // pour un visiteur anonyme.
        if (true !== ($payload['withdrawalWaiverAccepted'] ?? null)) {
            return $this->json([
                'detail' => 'Tu dois confirmer renoncer à ton droit de rétractation pour un accès immédiat avant de continuer.',
            ], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        // `redirectPath` vient du client (chemin du match affiché au moment du
        // clic, voir MatchDetailView.vue/PaywallModal.vue) : on n'accepte
        // qu'un chemin interne commençant par "/" — jamais une URL absolue —
        // pour ne jamais construire une success_url/cancel_url Stripe pointant
        // vers un domaine arbitraire à partir d'une valeur envoyée par le client.
        $safeRedirectPath = (is_string($redirectPath) && str_starts_with($redirectPath, '/') && !str_starts_with($redirectPath, '//'))
            ? $redirectPath
            : '/matchs';

        /** @var User|null $user */
        $user = $this->getUser();

        $checkoutUrl = $this->stripeCheckoutService->createCheckoutSessionUrl(
            $user,
            $plan,
            $safeRedirectPath,
            withdrawalWaiverAcceptedAt: new \DateTimeImmutable(),
        );

        return $this->json(['checkoutUrl' => $checkoutUrl]);
    }
}

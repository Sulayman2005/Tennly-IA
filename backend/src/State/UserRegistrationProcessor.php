<?php

namespace App\State;

use ApiPlatform\Metadata\Operation;
use ApiPlatform\State\ProcessorInterface;
use App\Entity\Plan;
use App\Entity\User;
use App\Repository\PlanRepository;
use App\Service\StripeCheckoutService;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\PasswordHasher\Hasher\UserPasswordHasherInterface;

/**
 * Traite POST /api/register.
 *
 * C'est le SEUL point d'entrée qui crée un compte. Conformément au cahier des
 * charges section 3.9 : le frontend Vue n'appelle cet endpoint qu'après le
 * clic sur "Continuer vers le paiement" dans l'écran de connexion, lui-même
 * atteint uniquement depuis une formule choisie dans la popup paywall
 * (section 3.2.1) — jamais depuis un bouton d'inscription libre.
 *
 * @implements ProcessorInterface<User, User>
 */
final class UserRegistrationProcessor implements ProcessorInterface
{
    public function __construct(
        private readonly EntityManagerInterface $entityManager,
        private readonly UserPasswordHasherInterface $passwordHasher,
        private readonly PlanRepository $planRepository,
        private readonly StripeCheckoutService $stripeCheckoutService,
    ) {
    }

    public function process(mixed $data, Operation $operation, array $uriVariables = [], array $context = []): User
    {
        /** @var User $user */
        $user = $data;

        $user->setPassword($this->passwordHasher->hashPassword($user, (string) $user->getPlainPassword()));
        $user->eraseCredentials();

        $this->entityManager->persist($user);
        $this->entityManager->flush();

        // Si une formule a été transmise (paramètre ?plan= de connexion.html,
        // voir section 12.1.5), on démarre immédiatement le paiement Stripe —
        // la création du compte n'est jamais une étape isolée du paiement.
        if ($planCode = $user->getPlanCode()) {
            /** @var Plan|null $plan */
            $plan = $this->planRepository->findOneByCode($planCode);

            if (null !== $plan) {
                $checkoutUrl = $this->stripeCheckoutService->createCheckoutSessionUrl($user, $plan);
                $user->setCheckoutUrl($checkoutUrl);
            }
        }

        return $user;
    }
}

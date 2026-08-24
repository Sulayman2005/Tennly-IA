<?php

namespace App\State;

use ApiPlatform\Metadata\Operation;
use ApiPlatform\State\ProcessorInterface;
use App\Entity\User;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\PasswordHasher\Hasher\UserPasswordHasherInterface;

/**
 * Traite POST /api/register.
 *
 * C'est le SEUL point d'entrée qui crée un compte — mais, contrairement à la
 * version initiale du parcours (section 3.9), la création du compte
 * n'entraîne plus aucun paiement : un compte peut exister durablement sans
 * jamais être abonné. Le paiement se déclenche séparément, au moment où
 * l'utilisateur choisit une formule depuis la popup paywall d'un match
 * précis (voir CheckoutSessionController et PaywallModal.vue) — jamais
 * automatiquement à l'inscription.
 *
 * @implements ProcessorInterface<User, User>
 */
final class UserRegistrationProcessor implements ProcessorInterface
{
    public function __construct(
        private readonly EntityManagerInterface $entityManager,
        private readonly UserPasswordHasherInterface $passwordHasher,
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

        return $user;
    }
}



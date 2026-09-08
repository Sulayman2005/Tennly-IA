<?php

namespace App\Serializer;

use ApiPlatform\Serializer\SerializerContextBuilderInterface;
use App\Entity\TennisMatch;
use App\Entity\User;
use Symfony\Bundle\SecurityBundle\Security;
use Symfony\Component\HttpFoundation\Request;

/**
 * Le pronostic léger (favori + probabilité, section 3.2.1) qui apparaît dans
 * /api/tennis_matches était jusqu'ici visible par tout le monde, y compris
 * les visiteurs non connectés — TennisMatch::class n'a aucun attribut
 * `security` (contrairement à Prediction::class, dont l'opération Get exige
 * déjà un abonnement actif pour l'analyse complète). Décision produit
 * (02/09/2026) : ce pronostic léger doit lui aussi être réservé aux comptes
 * ROLE_ADMIN ou aux abonnés actifs.
 *
 * On ne peut pas faire ça avec un simple `security` sur TennisMatch — cette
 * ressource doit rester consultable publiquement pour tout le reste (nom des
 * joueurs, tournoi, date, statut : le "tableau des matchs" public, section
 * 3.2). Seul le champ `prediction` doit disparaître conditionnellement.
 *
 * D'où ce ContextBuilder : il ajoute le groupe `match:read:prediction`
 * (voir TennisMatch::$prediction) à la normalisation UNIQUEMENT si
 * l'utilisateur y a droit, avant que le Serializer ne s'exécute. Sans ce
 * groupe, la propriété $prediction disparaît entièrement de la réponse
 * (jamais un objet vide) — exactement l'effet recherché.
 */
final class TennisMatchContextBuilder implements SerializerContextBuilderInterface
{
    public function __construct(
        private readonly SerializerContextBuilderInterface $decorated,
        private readonly Security $security,
    ) {
    }

    public function createFromRequest(Request $request, bool $normalization, array $extractedAttributes = null): array
    {
        $context = $this->decorated->createFromRequest($request, $normalization, $extractedAttributes);

        if ($normalization && ($context['resource_class'] ?? null) === TennisMatch::class) {
            $user = $this->security->getUser();
            $hasPredictionAccess = $this->security->isGranted('ROLE_ADMIN')
                || ($user instanceof User && $user->hasActiveSubscription());

            if ($hasPredictionAccess) {
                $context['groups'][] = 'match:read:prediction';
            }
        }

        return $context;
    }
}
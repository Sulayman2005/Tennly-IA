<?php

namespace App\Tests\Entity;

use App\Entity\Player;
use PHPUnit\Framework\TestCase;
use Symfony\Component\Serializer\Annotation\Groups;

/**
 * Ce test existe directement à cause d'un vrai bug rencontré en prod (voir
 * historique du 28/08/2026) : la propriété `tour` ('atp'/'wta') existait
 * bien en base et dans les scripts ml-service, mais avait été oubliée dans
 * l'entité Player — ni colonne Doctrine, ni getter/setter, ni #[Groups(...)].
 * Résultat : l'API ne renvoyait jamais `tour`, et le badge ATP/WTA du
 * frontend retombait silencieusement sur "ATP" par défaut, quelle que soit
 * la vraie valeur en base — sans qu'aucune erreur ne remonte nulle part.
 *
 * Ces tests ne touchent ni la base ni le kernel Symfony (TestCase, pas
 * KernelTestCase) : ils vérifient juste la classe Player elle-même, donc ils
 * tournent en une fraction de seconde et peuvent servir de garde-fou
 * systématique avant tout commit.
 */
class PlayerTest extends TestCase
{
    public function testTourVautAtpParDefaut(): void
    {
        $player = new Player();

        $this->assertSame('atp', $player->getTour());
    }

    public function testSetTourEtGetTourFontBienUnAllerRetour(): void
    {
        $player = new Player();
        $player->setTour('wta');

        $this->assertSame('wta', $player->getTour());
    }

    /**
     * Le cœur du bug : si cette annotation disparaît un jour (à nouveau),
     * l'API arrête silencieusement de renvoyer `tour`, sans aucune erreur —
     * ce test est le seul filet qui l'attrape avant que ça arrive en prod.
     */
    public function testLaProprieteTourEstExposeeParGroupsPourLApi(): void
    {
        $property = new \ReflectionProperty(Player::class, 'tour');
        $attributes = $property->getAttributes(Groups::class);

        $this->assertNotEmpty(
            $attributes,
            'La propriété "tour" de Player doit porter #[Groups(...)], sinon '
            .'l\'API Platform ne la sérialise jamais (voir le bug du '
            .'28/08/2026 : le badge ATP/WTA retombait silencieusement sur '
            .'"ATP" côté frontend, quelle que soit la vraie valeur en base).'
        );

        /** @var Groups $groups */
        $groups = $attributes[0]->newInstance();

        $this->assertContains(
            'player:read',
            $groups->getGroups(),
            'Le groupe "player:read" doit être présent sur "tour" — c\'est '
            .'lui qui contrôle la sérialisation de GET /api/players et '
            .'GET /api/players/{id}.'
        );

        $this->assertContains(
            'match:read',
            $groups->getGroups(),
            'Le groupe "match:read" doit être présent sur "tour" — c\'est '
            .'lui qui contrôle si match.playerA.tour / match.playerB.tour '
            .'sont exposés sur GET /api/tennis_matches/{id} (voir le badge '
            .'de MatchDetailView.vue).'
        );
    }

    public function testGetTourEtSetTourExistentBienSurLaClasse(): void
    {
        $this->assertTrue(method_exists(Player::class, 'getTour'));
        $this->assertTrue(method_exists(Player::class, 'setTour'));
    }
}
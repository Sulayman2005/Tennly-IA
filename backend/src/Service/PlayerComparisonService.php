<?php

namespace App\Service;

use App\Entity\Player;
use App\Repository\PlayerRepository;
use Doctrine\DBAL\Connection;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\Process\Exception\ExceptionInterface as ProcessExceptionInterface;
use Symfony\Component\Process\Process;

/**
 * Comparateur de joueurs (roadmap post-lancement) : calcule une VRAIE analyse
 * (probabilité, confiance, facteurs, radar) entre deux joueurs choisis
 * librement — pas seulement ceux d'un match réel — réservée aux abonnés/à
 * l'admin (voir ComparateurController, même règle de sécurité que
 * Prediction::class).
 *
 * Comment ça marche, en bref :
 *  - Le classement/Elo viennent directement de Player (déjà en base).
 *  - Le service/retour/forme/repos/fatigue/exploit/main viennent de
 *    player_snapshot, une table rafraîchie CHAQUE JOUR par
 *    ml-service/import_upcoming_matches.py (voir son en-tête) — jamais
 *    recalculée ici, ce serait bien trop lent (il faudrait retélécharger et
 *    rejouer des années d'historique ATP à chaque comparaison).
 *  - Le face-à-face vient de player_head_to_head, rafraîchie par le même
 *    script, à partir de TOUT l'historique (pas seulement les quelques
 *    matchs affichés dans /matchs).
 *  - La probabilité elle-même vient du modèle XGBoost entraîné
 *    (train_model.py), via un appel en sous-processus à
 *    ml-service/predict_pair.py (aucun accès réseau/base de données côté
 *    Python ici : seulement le calcul du modèle, donc rapide). Si le modèle
 *    n'est pas disponible (xgboost pas installé, pas encore entraîné, ou le
 *    sous-processus échoue pour une raison quelconque), on retombe
 *    silencieusement sur la même formule Elo que le reste de l'app —
 *    jamais d'erreur HTTP pour l'utilisateur à cause de ça.
 *
 * NOTE (29/08/2026) : `tour_is_wta` fait partie de REQUIRED_KEYS côté
 * ml-service/predict_pair.py (c'est la dernière feature du modèle entraîné,
 * voir train_model.py) — tant qu'elle manquait dans le payload envoyé ici,
 * predict_pair.py renvoyait systématiquement {"model_available": false,
 * "error": "Clé(s) manquante(s)... tour_is_wta"}, donc le Comparateur
 * retombait TOUJOURS sur la formule Elo, quels que soient les deux joueurs
 * choisis — jamais réellement le modèle XGBoost. Ça expliquait aussi
 * pourquoi le facteur "Classement" affichait toujours "ATP" en dur : le
 * libellé n'était jamais calculé dynamiquement à partir du circuit réel des
 * joueurs comparés. Les deux sont corrigés ci-dessous.
 */
class PlayerComparisonService
{
    private const VALID_SURFACES = ['dur', 'terre_battue', 'gazon'];

    // Même identifiant que ml-service/import_real_data.py /
    // import_upcoming_matches.py pour la formule de repli — voir leur propre
    // constante MODEL_VERSION.
    private const ELO_FALLBACK_MODEL_VERSION = 'elo-surface-stats-2026.08';

    public function __construct(
        private readonly Connection $connection,
        private readonly PlayerRepository $playerRepository,
        #[Autowire('%kernel.project_dir%')] private readonly string $projectDir,
    ) {
    }

    /**
     * @throws \InvalidArgumentException si les ids de joueur ou la surface
     *                                   sont invalides (à traduire en 400 par
     *                                   le contrôleur)
     */
    public function analyser(int $playerAId, int $playerBId, string $surface): array
    {
        if ($playerAId === $playerBId) {
            throw new \InvalidArgumentException('Choisis deux joueurs différents.');
        }
        if (!in_array($surface, self::VALID_SURFACES, true)) {
            throw new \InvalidArgumentException(
                sprintf('Surface invalide : "%s" (attendu : %s).', $surface, implode(', ', self::VALID_SURFACES))
            );
        }

        $playerA = $this->playerRepository->find($playerAId);
        $playerB = $this->playerRepository->find($playerBId);
        if (!$playerA || !$playerB) {
            throw new \InvalidArgumentException('Joueur introuvable.');
        }

        $snapshotA = $this->fetchSnapshot($playerAId);
        $snapshotB = $this->fetchSnapshot($playerBId);
        [$h2hA, $h2hB] = $this->fetchHeadToHead($playerAId, $playerBId);

        $eloSurfaceA = $this->eloForSurface($playerA, $surface);
        $eloSurfaceB = $this->eloForSurface($playerB, $surface);

        // Le modèle a été entraîné sur ATP+WTA combinés avec le circuit comme
        // simple feature (voir ml-service/train_model.py, tour_is_wta) — une
        // info par PAIRE, pas par joueur (les deux joueurs d'un vrai match
        // sont toujours du même circuit). Le comparateur, lui, ne bloque pas
        // un choix de deux joueurs de circuits différents : dans ce cas rare
        // et peu sensé sportivement, l'analyse reste calée sur le circuit du
        // joueur A uniquement — voir aussi la note "crossTour" côté
        // frontend (ComparateurView.vue), qui prévient l'utilisateur de ce
        // cas précis.
        $tourIsWta = $playerA->getTour() === 'wta' ? 1 : 0;

        $serveA = $snapshotA['serve_score'] ?? 60.0;
        $serveB = $snapshotB['serve_score'] ?? 60.0;
        $returnA = $snapshotA['return_score'] ?? 60.0;
        $returnB = $snapshotB['return_score'] ?? 60.0;
        $momentumA = $this->nullableFloat($snapshotA['momentum'] ?? null);
        $momentumB = $this->nullableFloat($snapshotB['momentum'] ?? null);
        $formA = $this->nullableFloat($snapshotA['recent_form'] ?? null);
        $formB = $this->nullableFloat($snapshotB['recent_form'] ?? null);
        $restA = $this->nullableFloat($snapshotA['days_rest'] ?? null);
        $restB = $this->nullableFloat($snapshotB['days_rest'] ?? null);
        $fatigueA = $this->nullableFloat($snapshotA['fatigue_minutes'] ?? null);
        $fatigueB = $this->nullableFloat($snapshotB['fatigue_minutes'] ?? null);
        $upsetA = $this->nullableFloat($snapshotA['upset_rate'] ?? null);
        $upsetB = $this->nullableFloat($snapshotB['upset_rate'] ?? null);

        // Avantage main : seulement si les deux joueurs ont une main connue
        // et différente — même règle que ml-service/import_real_data.py.
        // On pioche la valeur précalculée côté joueur A pour un adversaire
        // de la main de B, et inversement (voir winrate_vs_left/right dans
        // player_snapshot).
        $handA = $playerA->getDominantHand();
        $handB = $playerB->getDominantHand();
        $handEdgeA = null;
        $handEdgeB = null;
        if (in_array($handA, ['L', 'R'], true) && in_array($handB, ['L', 'R'], true) && $handA !== $handB) {
            $handEdgeA = $this->nullableFloat($snapshotA[$handB === 'L' ? 'winrate_vs_left' : 'winrate_vs_right'] ?? null);
            $handEdgeB = $this->nullableFloat($snapshotB[$handA === 'L' ? 'winrate_vs_left' : 'winrate_vs_right'] ?? null);
        }

        // Signal "habitude du jeu en intérieur" volontairement absent ici :
        // il ne dépend pas de la surface mais du toit du court (indoor bool),
        // une notion qui n'existe pas pour un match hypothétique entre deux
        // joueurs sans date ni lieu — voir la même limite assumée dans
        // ml-service/import_upcoming_matches.py (docstring, "indoor").

        [$probaAWins, $modelVersion, $modelAvailable] = $this->predict(
            $playerA->getAtpWtaRank(), $playerB->getAtpWtaRank(),
            $playerA->getEloOverall(), $playerB->getEloOverall(),
            $eloSurfaceA, $eloSurfaceB,
            $serveA, $serveB, $returnA, $returnB,
            $momentumA, $momentumB, $formA, $formB, $restA, $restB,
            $h2hA, $h2hB, $handEdgeA, $handEdgeB, $fatigueA, $fatigueB, $upsetA, $upsetB,
            $tourIsWta,
        );

        $isAFav = $probaAWins >= 0.5;
        $proba = $isAFav ? $probaAWins : 1 - $probaAWins;
        $confidence = self::confidenceFromProbability($proba);
        $favoriteId = $isAFav ? $playerA->getId() : $playerB->getId();

        $factors = $this->buildFactors(
            $isAFav,
            $playerA->getAtpWtaRank(), $playerB->getAtpWtaRank(),
            $eloSurfaceA, $eloSurfaceB,
            $h2hA, $h2hB, $serveA, $serveB, $momentumA, $momentumB,
            $handEdgeA, $handEdgeB, $handA, $handB,
            $fatigueA, $fatigueB, $upsetA, $upsetB,
            $tourIsWta,
        );

        $radar = [
            'eloSurface' => [self::clampValue(($eloSurfaceA - 1500) / 8), self::clampValue(($eloSurfaceB - 1500) / 8)],
            'forme' => [self::percentOrDefault($formA), self::percentOrDefault($formB)],
            'service' => [self::clampValue($serveA), self::clampValue($serveB)],
            'retour' => [self::clampValue($returnA), self::clampValue($returnB)],
            'repos' => [self::clampValue(($restA ?? 3) * 10), self::clampValue(($restB ?? 3) * 10)],
            'h2h' => [self::clampValue(50 + ($h2hA - $h2hB) * 10), self::clampValue(50 - ($h2hA - $h2hB) * 10)],
        ];

        return [
            'playerA' => ['id' => $playerA->getId(), 'fullName' => $playerA->getFullName()],
            'playerB' => ['id' => $playerB->getId(), 'fullName' => $playerB->getFullName()],
            'surface' => $surface,
            'favoritePlayerId' => $favoriteId,
            'probabilityFavorite' => round($proba, 4),
            'confidenceLevel' => $confidence,
            'modelVersion' => $modelVersion,
            'modelAvailable' => $modelAvailable,
            'factors' => $factors,
            'radar' => $radar,
        ];
    }

    /** @return array<string, mixed> tableau vide si aucun instantané (joueur sans historique TML connu) */
    private function fetchSnapshot(int $playerId): array
    {
        $row = $this->connection->fetchAssociative(
            'SELECT serve_score, return_score, momentum, recent_form, days_rest, fatigue_minutes, '
            . 'upset_rate, winrate_vs_left, winrate_vs_right FROM player_snapshot WHERE player_id = ?',
            [$playerId]
        );

        return $row === false ? [] : $row;
    }

    /** @return array{0: int, 1: int} [victoires joueur A, victoires joueur B] */
    private function fetchHeadToHead(int $playerAId, int $playerBId): array
    {
        $low = min($playerAId, $playerBId);
        $high = max($playerAId, $playerBId);

        $row = $this->connection->fetchAssociative(
            'SELECT wins_low, wins_high FROM player_head_to_head WHERE player_low_id = ? AND player_high_id = ?',
            [$low, $high]
        );

        if ($row === false) {
            return [0, 0];
        }

        return $playerAId === $low
            ? [(int) $row['wins_low'], (int) $row['wins_high']]
            : [(int) $row['wins_high'], (int) $row['wins_low']];
    }

    private function eloForSurface(Player $player, string $surface): float
    {
        return match ($surface) {
            'terre_battue' => $player->getEloClay(),
            'gazon' => $player->getEloGrass(),
            default => $player->getEloHard(), // 'dur'
        };
    }

    private function nullableFloat(mixed $value): ?float
    {
        return $value === null ? null : (float) $value;
    }

    /**
     * Appelle ml-service/predict_pair.py en sous-processus. Ne lève JAMAIS —
     * en cas d'échec (python introuvable, xgboost non installé, modèle pas
     * encore entraîné, sortie invalide…), retombe sur la formule Elo, comme
     * les scripts d'import Python le font déjà eux-mêmes.
     *
     * @return array{0: float, 1: string, 2: bool} [probabilité que A gagne, version du modèle utilisé, modèle réellement utilisé ?]
     */
    private function predict(
        ?int $rankA, ?int $rankB,
        float $eloOverallA, float $eloOverallB,
        float $eloSurfaceA, float $eloSurfaceB,
        float $serveA, float $serveB, float $returnA, float $returnB,
        ?float $momentumA, ?float $momentumB, ?float $formA, ?float $formB, ?float $restA, ?float $restB,
        int $h2hA, int $h2hB, ?float $handEdgeA, ?float $handEdgeB, ?float $fatigueA, ?float $fatigueB,
        ?float $upsetA, ?float $upsetB, int $tourIsWta,
    ): array {
        $eloFallback = 1.0 / (1.0 + 10 ** (($eloSurfaceB - $eloSurfaceA) / 400.0));

        $payload = [
            'rank1' => $rankA, 'rank2' => $rankB,
            'elo_overall1' => $eloOverallA, 'elo_overall2' => $eloOverallB,
            'elo_surface1' => $eloSurfaceA, 'elo_surface2' => $eloSurfaceB,
            'serve1' => $serveA, 'serve2' => $serveB,
            'return1' => $returnA, 'return2' => $returnB,
            'momentum1' => $momentumA, 'momentum2' => $momentumB,
            'form1' => $formA, 'form2' => $formB,
            'rest1' => $restA, 'rest2' => $restB,
            'h2h1' => $h2hA, 'h2h2' => $h2hB,
            'hand_edge1' => $handEdgeA, 'hand_edge2' => $handEdgeB,
            'fatigue1' => $fatigueA, 'fatigue2' => $fatigueB,
            'indoor1' => null, 'indoor2' => null,
            'upset1' => $upsetA, 'upset2' => $upsetB,
            // NOTE (29/08/2026) : manquait ici — voir la docstring de classe
            // en tête de fichier. predict_pair.py exige cette clé
            // (REQUIRED_KEYS), donc son absence faisait échouer le modèle en
            // silence à chaque appel, systématiquement, quels que soient les
            // deux joueurs comparés.
            'tour_is_wta' => $tourIsWta,
        ];

        try {
            // Le binaire python est configurable (ta venv n'est pas forcément
            // celle du processus qui lance Symfony) — voir
            // ML_SERVICE_PYTHON_BIN dans ton .env.local, défaut "python".
            $pythonBin = $_ENV['ML_SERVICE_PYTHON_BIN'] ?? getenv('ML_SERVICE_PYTHON_BIN') ?: 'python';
            $scriptPath = $this->projectDir . '/../ml-service/predict_pair.py';

            $process = new Process([$pythonBin, $scriptPath]);
            $process->setInput(json_encode($payload, JSON_THROW_ON_ERROR));
            $process->setTimeout(15);
            $process->run();

            if ($process->isSuccessful()) {
                $result = json_decode($process->getOutput(), true, flags: JSON_THROW_ON_ERROR);
                if (($result['model_available'] ?? false) === true && isset($result['probability_player1'])) {
                    return [(float) $result['probability_player1'], (string) $result['model_version'], true];
                }
            }
        } catch (ProcessExceptionInterface|\JsonException $e) {
            // Python introuvable, timeout, sortie invalide… -> repli silencieux ci-dessous.
        }

        return [$eloFallback, self::ELO_FALLBACK_MODEL_VERSION, false];
    }

    private static function confidenceFromProbability(float $p): string
    {
        if ($p >= 0.65) {
            return 'eleve';
        }
        if ($p >= 0.55) {
            return 'moyen';
        }

        return 'faible';
    }

    private static function clampValue(float $value, int $lo = 1, int $hi = 99): int
    {
        return (int) max($lo, min($hi, round($value)));
    }

    private static function percentOrDefault(?float $value, int $default = 65): int
    {
        return $value === null ? $default : self::clampValue($value * 100);
    }

    /**
     * Mêmes seuils/formules que ml-service/import_real_data.py (facteurs
     * d'explication) — recopiés ici volontairement (voir docstring de
     * predict_pair.py : le calcul du modèle lui-même reste dans Python, mais
     * cette présentation-là n'a pas besoin de repasser par un sous-processus).
     */
    private function buildFactors(
        bool $isAFav,
        ?int $rankA, ?int $rankB,
        float $eloA, float $eloB,
        int $h2hA, int $h2hB,
        float $serveA, float $serveB,
        ?float $momentumA, ?float $momentumB,
        ?float $handEdgeA, ?float $handEdgeB, ?string $handA, ?string $handB,
        ?float $fatigueA, ?float $fatigueB,
        ?float $upsetA, ?float $upsetB,
        int $tourIsWta,
    ): array {
        [$rankFav, $rankDog] = $isAFav ? [$rankA, $rankB] : [$rankB, $rankA];
        [$eloFav, $eloDog] = $isAFav ? [$eloA, $eloB] : [$eloB, $eloA];
        [$h2hFav, $h2hDog] = $isAFav ? [$h2hA, $h2hB] : [$h2hB, $h2hA];
        [$serveFav, $serveDog] = $isAFav ? [$serveA, $serveB] : [$serveB, $serveA];
        [$momentumFav, $momentumDog] = $isAFav ? [$momentumA, $momentumB] : [$momentumB, $momentumA];
        [$handEdgeFav, $handEdgeDog] = $isAFav ? [$handEdgeA, $handEdgeB] : [$handEdgeB, $handEdgeA];
        $handDog = $isAFav ? $handB : $handA;
        [$fatigueFav, $fatigueDog] = $isAFav ? [$fatigueA, $fatigueB] : [$fatigueB, $fatigueA];
        [$upsetFav, $upsetDog] = $isAFav ? [$upsetA, $upsetB] : [$upsetB, $upsetA];

        $factors = [];

        if ($rankFav !== null && $rankDog !== null) {
            $factors[] = [
                // NOTE (29/08/2026) : "Classement ATP" était écrit en dur ici
                // auparavant — toujours affiché, même pour deux joueuses WTA
                // (voir le bug du Comparateur : Elvina Kalieva / Vendula
                // Valdmannova). Le libellé suit maintenant le vrai circuit,
                // comme le fait déjà ml-service/import_real_data.py.
                'label' => $tourIsWta === 1 ? 'Classement WTA' : 'Classement ATP',
                'favors' => $isAFav ? 'A' : 'B',
                'impactPoints' => round(abs($rankFav - $rankDog) / 10, 1),
                'tone' => 'ok',
            ];
        }
        if (($h2hFav + $h2hDog) > 0) {
            $factors[] = [
                'label' => 'Face-à-face',
                'favors' => ($isAFav === ($h2hFav >= $h2hDog)) ? 'A' : 'B',
                'impactPoints' => $h2hFav - $h2hDog,
                'tone' => $h2hFav >= $h2hDog ? 'ok' : 'warn',
            ];
        }
        if (abs($serveFav - $serveDog) >= 8) {
            $factors[] = [
                'label' => 'Force au service',
                'favors' => ($isAFav === ($serveFav >= $serveDog)) ? 'A' : 'B',
                'impactPoints' => round(($serveFav - $serveDog) / 10, 1),
                'tone' => $serveFav >= $serveDog ? 'ok' : 'warn',
            ];
        }
        if ($momentumFav !== null && $momentumDog !== null && abs($momentumFav - $momentumDog) >= 15) {
            $factors[] = [
                'label' => 'Dynamique du moment (Elo sur les derniers matchs)',
                'favors' => ($isAFav === ($momentumFav >= $momentumDog)) ? 'A' : 'B',
                'impactPoints' => round(($momentumFav - $momentumDog) / 10, 1),
                'tone' => $momentumFav >= $momentumDog ? 'ok' : 'warn',
            ];
        }
        if ($handEdgeFav !== null && $handEdgeDog !== null && abs($handEdgeFav - $handEdgeDog) >= 0.15) {
            $style = $handDog === 'L' ? 'gaucher' : 'droitier';
            $factors[] = [
                'label' => "Habitude du jeu face à un {$style}",
                'favors' => ($isAFav === ($handEdgeFav >= $handEdgeDog)) ? 'A' : 'B',
                'impactPoints' => round(($handEdgeFav - $handEdgeDog) * 10, 1),
                'tone' => $handEdgeFav >= $handEdgeDog ? 'ok' : 'warn',
            ];
        }
        if ($fatigueFav !== null && $fatigueDog !== null && abs($fatigueFav - $fatigueDog) >= 60) {
            $moreRestedIsFav = $fatigueFav <= $fatigueDog;
            $factors[] = [
                'label' => 'Fatigue récente (minutes jouées sur les 10 derniers jours)',
                'favors' => $isAFav === $moreRestedIsFav ? 'A' : 'B',
                'impactPoints' => round(($fatigueDog - $fatigueFav) / 30, 1),
                'tone' => $moreRestedIsFav ? 'ok' : 'warn',
            ];
        }
        if ($upsetFav !== null && $upsetDog !== null && abs($upsetFav - $upsetDog) >= 0.15) {
            $factors[] = [
                'label' => "Capacité à créer l'exploit contre plus fort classé",
                'favors' => ($isAFav === ($upsetFav >= $upsetDog)) ? 'A' : 'B',
                'impactPoints' => round(($upsetFav - $upsetDog) * 10, 1),
                'tone' => $upsetFav >= $upsetDog ? 'ok' : 'warn',
            ];
        }

        if (empty($factors)) {
            $factors[] = [
                'label' => 'Estimation Elo (historique insuffisant pour affiner)',
                'favors' => $isAFav ? 'A' : 'B',
                'impactPoints' => round(abs($eloFav - $eloDog) / 20, 1),
                'tone' => 'ok',
            ];
        }

        return $factors;
    }
}


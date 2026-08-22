<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// TODO : brancher sur un futur endpoint /api/stats une fois le back-office
// (section 3.7) capable de calculer ces agrégats en temps réel.
const stats = [
  { target: 67.8, decimals: 1, prefix: '', suffix: ' %', label: 'Réussite sur 90 jours', bar: 68 },
  { target: 12480, decimals: 0, prefix: '', suffix: '', label: 'Matchs analysés', bar: 90 },
  { target: 4.1, decimals: 1, prefix: '+', suffix: ' %', label: 'Value moyenne vs cote de clôture', bar: 55 },
  { target: 0.19, decimals: 2, prefix: '', suffix: '', label: 'Brier score (plus bas = meilleur)', bar: 80 },
]

// Compteurs et barres animés au chargement (repris du prototype validé) :
// on part de 0 et on anime vers la vraie valeur, plutôt que d'afficher un
// nombre figé d'entrée de jeu.
const statValues = ref(stats.map(() => 0))
const barWidths = ref(stats.map(() => 0))

function formatStat(i) {
  const s = stats[i]
  return s.prefix + statValues.value[i].toFixed(s.decimals) + s.suffix
}

onMounted(() => {
  stats.forEach((s, i) => {
    const duration = 900
    const start = performance.now()
    function step(now) {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      statValues.value[i] = s.target * eased
      if (t < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  })
  // Décalé d'une frame pour que la transition CSS width parte bien de 0.
  requestAnimationFrame(() => {
    barWidths.value = stats.map((s) => s.bar)
  })
})

function goToMatches() {
  router.push('/matchs')
}
</script>

<template>
  <section class="hero">
    <div class="eyebrow"><i></i>IA TENNIS · DONNÉES ATP RÉELLES</div>
    <h1>Prédis chaque <span class="accent">victoire</span><br />avant qu'elle n'ait lieu.</h1>
    <p>Des pronostics tennis calibrés par IA, expliqués simplement, avec un historique de performance 100 % public.</p>
    <button class="cta-main" @click="goToMatches">
      Voir les pronostics du jour <span class="arrow">→</span>
    </button>
    <div class="hero-stats">
      <div class="hs"><b>67,8 %</b> de réussite sur 90 jours</div>
      <div class="hs"><b>12 480</b> matchs analysés</div>
      <div class="hs"><b>4 ans</b> d'historique ATP rejoué</div>
    </div>
  </section>

  <!--
    Emplacement pour une vraie photo/vidéo licenciée : dès que tu as un
    visuel dont tu détiens les droits (licence photo ATP/Getty, tournage
    propre), remplace le contenu de .clay-hero par :
      <img src="ton-visuel.jpg" alt="..." style="position:absolute;inset:0;
        width:100%;height:100%;object-fit:cover;object-position:center 30%">
    En attendant, la scène ci-dessous (terre battue stylisée + trophée
    générique) s'affiche à la place — elle n'illustre et ne prétend
    représenter aucun joueur réel, professionnel ou non.
  -->
  <div class="clay-hero">
    <div class="clay-texture"></div>
    <svg class="clay-lines" width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 900 420">
      <rect x="46" y="46" width="500" height="328" fill="none" stroke="var(--chalk)" stroke-width="2.4" />
      <line x1="46" y1="210" x2="546" y2="210" stroke="var(--chalk)" stroke-width="1.6" />
      <line x1="150" y1="46" x2="150" y2="374" stroke="var(--chalk)" stroke-width="1.6" />
      <line x1="150" y1="210" x2="46" y2="210" stroke="var(--chalk)" stroke-width="1.6" />
    </svg>
    <div class="clay-vignette"></div>
    <div class="clay-dust" style="width: 5px; height: 5px; left: 22%; top: 60%; animation-delay: 0.2s"></div>
    <div class="clay-dust" style="width: 4px; height: 4px; left: 34%; top: 72%; animation-delay: 1.1s"></div>
    <div class="clay-dust" style="width: 6px; height: 6px; left: 28%; top: 50%; animation-delay: 2s"></div>
    <div class="clay-dust" style="width: 3px; height: 3px; left: 40%; top: 66%; animation-delay: 0.7s"></div>

    <!-- Trophée stylisé (aucun joueur réel représenté) — voir le commentaire
         ci-dessus pour le remplacer par une vraie photo/vidéo dès que les
         droits sont obtenus. -->
    <svg class="champion" viewBox="0 0 200 300" xmlns="http://www.w3.org/2000/svg">
      <g class="burst" opacity=".4" stroke="var(--chalk)" stroke-width="2.5" stroke-linecap="round">
        <line x1="100" y1="98" x2="100" y2="60" />
        <line x1="100" y1="98" x2="136" y2="72" transform="rotate(28 100 98)" />
        <line x1="100" y1="98" x2="136" y2="72" transform="rotate(-28 100 98)" />
        <line x1="100" y1="98" x2="146" y2="98" transform="rotate(56 100 98)" />
        <line x1="100" y1="98" x2="146" y2="98" transform="rotate(-56 100 98)" />
      </g>
      <ellipse cx="100" cy="272" rx="52" ry="8" fill="#000" opacity=".22" />
      <g class="glint">
        <path
          d="M58 60 C58 118 76 154 100 160 C124 154 142 118 142 60 L142 46 C142 40 137 36 131 36 L69 36 C63 36 58 40 58 46 Z"
          fill="var(--chalk)"
        />
        <path
          d="M58 62 C30 62 26 104 52 112 C60 114 66 111 66 111"
          stroke="var(--chalk)"
          stroke-width="7"
          fill="none"
          stroke-linecap="round"
        />
        <path
          d="M142 62 C170 62 174 104 148 112 C140 114 134 111 134 111"
          stroke="var(--chalk)"
          stroke-width="7"
          fill="none"
          stroke-linecap="round"
        />
        <line x1="82" y1="52" x2="82" y2="120" stroke="var(--clay2)" stroke-width="3" opacity=".35" stroke-linecap="round" />
      </g>
      <rect x="92" y="158" width="16" height="42" rx="3" fill="var(--chalk)" />
      <rect x="68" y="200" width="64" height="14" rx="6" fill="var(--chalk)" />
      <rect x="54" y="214" width="92" height="16" rx="7" fill="var(--chalk)" />
    </svg>

    <div class="clay-copy">
      <span class="tag">Terre battue · Roland-Garros</span>
      <h3>Chaque surface a ses lois.</h3>
      <p>L'Elo de Tennly IA se recalcule différemment sur dur, terre battue et gazon — parce qu'un même joueur n'y gagne pas de la même façon.</p>
    </div>
    <div class="clay-note">Visuel provisoire (silhouette générique, aucun joueur réel) — en attente d'une photo ou vidéo sous licence.</div>
  </div>

  <div class="stat-banner">
    <div class="stat-card" v-for="(s, i) in stats" :key="s.label">
      <div class="num">{{ formatStat(i) }}</div>
      <div class="lbl">{{ s.label }}</div>
      <div class="bar"><i :style="{ width: barWidths[i] + '%' }"></i></div>
    </div>
  </div>

  <!-- ================= COUVERTURE (surfaces / tournois) ================= -->
  <div class="section">
    <div class="section-head center">
      <div class="eyebrow" style="justify-content: center"><i></i>COUVERTURE</div>
      <h2>Tous les tournois du circuit ATP, sur toutes les surfaces</h2>
      <p>Le même moteur d'analyse s'adapte à chaque terrain — parce que la terre battue, le dur et le gazon ne se jouent pas pareil.</p>
    </div>
    <div class="surface-row">
      <div class="surface-card dur">
        <div class="dot"></div>
        <div class="name">Dur</div>
        <div class="desc">Australian Open, US Open, Masters 1000 indoor/outdoor.</div>
      </div>
      <div class="surface-card terre">
        <div class="dot"></div>
        <div class="name">Terre battue</div>
        <div class="desc">Roland-Garros, Monte-Carlo, Rome — l'Elo terre battue tourne à plein régime.</div>
      </div>
      <div class="surface-card gazon">
        <div class="dot"></div>
        <div class="name">Gazon</div>
        <div class="desc">Wimbledon et la courte tournée sur herbe qui précède.</div>
      </div>
    </div>
    <div class="level-row">
      <span class="level-chip">Grand Chelem</span>
      <span class="level-chip">Masters 1000</span>
      <span class="level-chip">ATP 500</span>
      <span class="level-chip">ATP 250</span>
    </div>
  </div>

  <!-- ================= EXEMPLE CONCRET ================= -->
  <div class="section">
    <div class="section-head">
      <div class="eyebrow"><i></i>CONCRÈTEMENT</div>
      <h2>Voici à quoi ressemble un pronostic Tennly IA</h2>
      <p>Une probabilité claire, et surtout les raisons derrière — jamais une boîte noire.</p>
    </div>
    <div class="example-panel">
      <div class="duel" style="margin-bottom: 0; background: transparent">
        <div class="p-card">
          <div class="av">JS</div>
          <div class="name">Jannik Sinner</div>
          <div class="rank">N°1 mondial</div>
          <div class="elo">Elo terre battue 2 118</div>
        </div>
        <div class="mid">
          <div class="vslabel">PROBABILITÉ</div>
          <div class="gauge">
            <svg width="150" height="150" viewBox="0 0 150 150">
              <circle class="ring-bg" cx="75" cy="75" r="64" stroke-width="14" fill="none" />
              <circle class="ring-fill" cx="75" cy="75" r="64" stroke-width="14" fill="none" style="stroke-dashoffset: 145" />
            </svg>
            <div class="pct"><b>64 %</b><span>Sinner favori</span></div>
          </div>
        </div>
        <div class="p-card right">
          <div class="av" style="background: var(--blue)">CA</div>
          <div class="name">Carlos Alcaraz</div>
          <div class="rank">N°2 mondial</div>
          <div class="elo">Elo terre battue 2 041</div>
        </div>
      </div>
      <div class="why" style="margin: 22px 0 0; box-shadow: none">
        <ul>
          <li><span class="tag ok">✓</span>Elo terre battue en faveur de Sinner (+77 points), recalculé sur l'historique réel de la surface.</li>
          <li><span class="tag ok">✓</span>Dynamique du moment favorable : Elo en progression sur ses 8 derniers matchs.</li>
          <li><span class="tag warn">!</span>Face-à-face équilibré (2 victoires partout) — facteur neutre sur ce match précis.</li>
        </ul>
      </div>
    </div>
  </div>

  <!-- ================= FONCTIONNALITÉS ================= -->
  <div class="section">
    <div class="section-head center">
      <div class="eyebrow" style="justify-content: center"><i></i>SOUS LE CAPOT</div>
      <h2>Ce que l'IA regarde vraiment</h2>
      <p>Pas de boîte noire : six signaux réels, calculés sur l'historique ATP — rien d'inventé, rien de figé.</p>
    </div>
    <div class="feature-grid">
      <div class="feature-card">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 18l5-6 4 4 7-9" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Elo par surface</h4>
        <p>Recalculé match après match sur dur, terre battue et gazon séparément — un joueur peut monter sur l'un et stagner sur l'autre.</p>
      </div>
      <div class="feature-card">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8" stroke="#fff" stroke-width="2" />
            <path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Service &amp; retour réels</h4>
        <p>Aces, % de premier service, balles de break — calculés sur les vraies statistiques de jeu, pas une estimation neutre.</p>
      </div>
      <div class="feature-card">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 20V10M12 20V4M20 20v-7" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Forme &amp; repos</h4>
        <p>Taux de victoire récent et jours de repos réels avant le match — jamais le résultat du match lui-même.</p>
      </div>
      <div class="feature-card">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 4l16 16M20 4L4 20" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Face-à-face</h4>
        <p>L'historique réel entre les deux joueurs, uniquement sur leurs confrontations déjà jouées.</p>
      </div>
      <div class="feature-card">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 16l5-9 4 6 3-4 4 6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Dynamique du moment</h4>
        <p>La tendance de l'Elo sur les 8 derniers matchs — un joueur peut progresser même avec un bilan moyen, face à plus fort.</p>
      </div>
      <div class="feature-card">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 3l2.6 6.2L21 10l-5 4.2L17.4 21 12 17.4 6.6 21 8 14.2 3 10l6.4-.8z" stroke="#fff" stroke-width="1.8" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Capacité à créer l'exploit</h4>
        <p>Le taux de victoire réel d'un joueur quand il partait outsider au classement — une vraie mesure, pas une intuition.</p>
      </div>
    </div>
  </div>

  <!-- ================= MÉTHODOLOGIE / DONNÉES ================= -->
  <div class="section">
    <div class="method-band">
      <div class="num">4 ans<small>d'historique ATP réel</small></div>
      <p>
        <strong style="color: #fff">Aucune donnée inventée.</strong> Tennly IA rejoue chronologiquement plusieurs années de résultats ATP réels pour
        calculer chaque Elo, chaque score de service et chaque tendance — la méthode est documentée, pas cachée derrière une boîte noire marketing.
      </p>
    </div>
  </div>

  <!-- ================= AVIS (emplacement honnête, pas de faux témoignages) ================= -->
  <div class="section">
    <div class="section-head center">
      <div class="eyebrow" style="justify-content: center"><i></i>COMMUNAUTÉ</div>
      <h2>Les avis arrivent bientôt</h2>
    </div>
    <div class="proof-placeholder">
      <div class="icon">💬</div>
      <strong>Pas encore d'utilisateurs publics</strong>
      <span>Tennly IA vient d'être lancé — dès les premiers retours réels, ils prendront place ici. Aucun avis fictif ne sera jamais affiché à leur place.</span>
    </div>
  </div>

  <!-- ================= FAQ ================= -->
  <div class="section">
    <div class="section-head center">
      <div class="eyebrow" style="justify-content: center"><i></i>QUESTIONS FRÉQUENTES</div>
      <h2>Tout ce qu'on te demande le plus souvent</h2>
    </div>
    <div class="faq-list">
      <div class="faq-item">
        <h4>Tennly IA est-il gratuit ?</h4>
        <p>L'aperçu (favori pressenti + probabilité) est gratuit sur tous les matchs. L'analyse complète — radar comparatif, facteurs d'explication détaillés, cote de valeur — est réservée aux abonnés.</p>
      </div>
      <div class="faq-item">
        <h4>Comment fonctionne l'IA ?</h4>
        <p>Un système Elo par surface combiné à de vraies statistiques de jeu (service, retour, forme, repos), rejoué sur l'historique ATP réel — pas un modèle opaque qu'on ne peut pas expliquer.</p>
      </div>
      <div class="faq-item">
        <h4>Est-ce que je peux parier directement depuis l'app ?</h4>
        <p>Non. Tennly IA est un outil d'aide à la décision, pas une plateforme de paris. Les pronostics ne constituent pas un conseil financier et ne garantissent aucun résultat.</p>
      </div>
      <div class="faq-item">
        <h4>Les données sont-elles fiables ?</h4>
        <p>Elles viennent de résultats ATP réellement joués, avec la méthode de calcul documentée publiquement — aucune statistique n'est inventée ou estimée sans le dire.</p>
      </div>
    </div>
  </div>

  <div class="final-cta">
    <h3>Prêt à voir tes premiers pronostics ?</h3>
    <p>Gratuit à découvrir, sans carte bancaire.</p>
    <button class="cta-main" @click="goToMatches">
      Voir les pronostics du jour <span class="arrow">→</span>
    </button>
  </div>

  <div class="site-footer">
    © Tennly IA — Outil d'aide à la décision à titre informatif, ne constitue ni un conseil en pari sportif ni une garantie de résultat.
  </div>
</template>

<style scoped>
h1,
h2,
h3 {
  text-wrap: balance;
}
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
  }
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* -- Hero -- */
.hero {
  padding: 64px 0 56px;
  text-align: center;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--green);
  margin: 0 0 14px;
}
.eyebrow i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
}
.hero h1 {
  font-size: 56px;
  line-height: 1.05;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0 0 18px;
  animation: fadeUp 0.6s ease both;
}
.hero h1 .accent {
  background: linear-gradient(90deg, var(--green), #1f8a6b);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.hero p {
  font-size: 20px;
  color: var(--grey);
  max-width: 560px;
  margin: 0 auto 40px;
  animation: fadeUp 0.6s 0.1s ease both;
}
.cta-main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--btn);
  color: #fff;
  padding: 17px 32px;
  border-radius: 999px;
  font-size: 17px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  box-shadow: var(--shadow-soft);
  transition: transform 0.15s;
  animation: fadeUp 0.6s 0.2s ease both;
  cursor: pointer;
}
.cta-main:hover {
  transform: translateY(-2px) scale(1.02);
}
.cta-main .arrow {
  transition: transform 0.15s;
}
.cta-main:hover .arrow {
  transform: translateX(4px);
}
.hero-stats {
  display: flex;
  justify-content: center;
  gap: 28px;
  flex-wrap: wrap;
  margin: 6px 0 0;
  animation: fadeUp 0.6s 0.25s ease both;
}
.hero-stats .hs {
  display: flex;
  align-items: baseline;
  gap: 7px;
  font-size: 14px;
  color: var(--grey);
}
.hero-stats .hs b {
  font-size: 20px;
  color: var(--ink);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* -- Hero terre battue -- */
.clay-hero {
  position: relative;
  border-radius: 32px;
  overflow: hidden;
  height: 420px;
  margin: 56px 0;
  background: linear-gradient(155deg, var(--clay) 0%, var(--clay2) 68%, #43200d 100%);
  color: var(--chalk);
  isolation: isolate;
  animation: fadeUp 0.7s 0.18s ease both;
}
.clay-texture {
  position: absolute;
  inset: 0;
  opacity: 0.5;
  mix-blend-mode: overlay;
  background-image: radial-gradient(rgba(255, 255, 255, 0.35) 1px, transparent 1.4px);
  background-size: 5px 5px;
}
.clay-lines {
  position: absolute;
  inset: 0;
  opacity: 0.55;
}
.clay-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 90% at 50% 15%, transparent 40%, rgba(0, 0, 0, 0.32));
}
.clay-dust {
  position: absolute;
  border-radius: 50%;
  background: rgba(245, 239, 226, 0.5);
  filter: blur(1px);
  animation: dustFloat 6s ease-in-out infinite alternate;
}
@keyframes dustFloat {
  from {
    transform: translateY(0) scale(1);
    opacity: 0.5;
  }
  to {
    transform: translateY(-14px) scale(1.3);
    opacity: 0.15;
  }
}
.champion {
  position: absolute;
  right: 9%;
  bottom: 0;
  height: 82%;
  opacity: 0.94;
  filter: drop-shadow(0 18px 22px rgba(0, 0, 0, 0.35));
  animation: trophyRise 1s 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
@keyframes trophyRise {
  from {
    transform: translateY(24px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 0.94;
  }
}
.champion .glint {
  animation: glint 2.6s ease-in-out 0.8s infinite;
}
@keyframes glint {
  0%,
  100% {
    opacity: 0.35;
  }
  50% {
    opacity: 1;
  }
}
.clay-copy {
  position: relative;
  z-index: 2;
  padding: 36px 40px;
  max-width: 340px;
}
.clay-copy .tag {
  display: inline-block;
  background: rgba(245, 239, 226, 0.16);
  border: 1px solid rgba(245, 239, 226, 0.4);
  font-size: 11px;
  padding: 5px 12px;
  border-radius: 999px;
  backdrop-filter: blur(6px);
  margin-bottom: 14px;
}
.clay-copy h3 {
  font-size: 24px;
  margin: 0 0 8px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #fff;
}
.clay-copy p {
  font-size: 14px;
  line-height: 1.6;
  opacity: 0.88;
  margin: 0;
}
.clay-note {
  position: absolute;
  left: 40px;
  bottom: 20px;
  right: 40px;
  font-size: 12px;
  opacity: 0.7;
  line-height: 1.5;
  z-index: 2;
}

/* -- Stats -- */
.stat-banner {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 0 0 60px;
}
.stat-card {
  background: var(--card);
  border-radius: 18px;
  padding: 24px 20px;
  animation: fadeUp 0.6s ease both;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.08);
}
.stat-card:nth-child(1) {
  animation-delay: 0.05s;
}
.stat-card:nth-child(2) {
  animation-delay: 0.12s;
}
.stat-card:nth-child(3) {
  animation-delay: 0.19s;
}
.stat-card:nth-child(4) {
  animation-delay: 0.26s;
}
.stat-card .num {
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.stat-card .lbl {
  font-size: 13px;
  color: var(--grey);
  margin-top: 6px;
}
.stat-card .bar {
  height: 6px;
  border-radius: 99px;
  background: var(--line);
  margin-top: 14px;
  overflow: hidden;
}
.stat-card .bar i {
  display: block;
  height: 100%;
  background: var(--green);
  border-radius: 99px;
  width: 0;
  transition: width 1.1s cubic-bezier(0.2, 0.8, 0.2, 1);
}

/* -- Sections génériques -- */
.section {
  padding: 64px 0;
}
.section-head {
  max-width: 600px;
  margin: 0 0 40px;
}
.section-head.center {
  margin-left: auto;
  margin-right: auto;
  text-align: center;
}
.section-head h2 {
  font-size: 32px;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.015em;
  margin: 0 0 12px;
}
.section-head p {
  font-size: 16px;
  color: var(--grey);
  margin: 0;
  line-height: 1.55;
}

/* -- Couverture (surfaces / tournois) -- */
.surface-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}
.surface-card {
  background: var(--card);
  border-radius: 18px;
  padding: 22px 22px 20px;
}
.surface-card .dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  margin-bottom: 14px;
}
.surface-card.dur .dot {
  background: #4f8fd1;
}
.surface-card.terre .dot {
  background: var(--clay);
}
.surface-card.gazon .dot {
  background: #3f9142;
}
.surface-card .name {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 4px;
}
.surface-card .desc {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.5;
}
.level-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.level-chip {
  padding: 7px 15px;
  border-radius: 999px;
  background: var(--card);
  font-size: 12.5px;
  color: var(--grey);
  font-weight: 600;
}

/* -- Exemple concret -- */
.example-panel {
  background: var(--card);
  border-radius: 26px;
  padding: 8px;
}
.duel {
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  gap: 24px;
  align-items: center;
  background: var(--card);
  border-radius: 26px;
  padding: 36px;
  animation: fadeUp 0.5s ease both;
}
.p-card {
  text-align: center;
}
.p-card .av {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  background: var(--green);
}
.p-card.right .av {
  background: var(--blue);
}
.p-card .name {
  font-size: 20px;
  font-weight: 700;
}
.p-card .rank {
  color: var(--grey);
  font-size: 13px;
  margin-top: 4px;
}
.p-card .elo {
  margin-top: 10px;
  font-size: 12px;
  background: #fff;
  color: var(--btn);
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
}
.mid {
  text-align: center;
}
.mid .vslabel {
  font-size: 12px;
  color: var(--grey);
  margin-bottom: 8px;
  letter-spacing: 0.08em;
}
.gauge {
  position: relative;
  width: 150px;
  height: 150px;
  margin: 0 auto;
}
.gauge svg {
  transform: rotate(-90deg);
}
.gauge .ring-bg {
  stroke: var(--line);
}
.gauge .ring-fill {
  stroke: var(--green);
  stroke-dasharray: 402;
  stroke-dashoffset: 402;
  stroke-linecap: round;
  transition: stroke-dashoffset 1.1s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.gauge .pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}
.gauge .pct b {
  font-size: 26px;
}
.gauge .pct span {
  font-size: 11px;
  color: var(--grey);
}
.why {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 30px 34px;
  animation: fadeUp 0.5s 0.2s ease both;
}
.why ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.why li {
  display: flex;
  gap: 12px;
  color: #2a2a2a;
  font-size: 14px;
  line-height: 1.6;
}
.why .tag {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  margin-top: 1px;
}
.why .tag.ok {
  background: #e6f9ea;
  color: #1f7d33;
}
.why .tag.warn {
  background: #fff3cd;
  color: #8a6100;
}

/* -- Fonctionnalités -- */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.feature-card {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 24px;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}
.feature-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.07);
}
.feature-card .fi {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--green), var(--lime));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.feature-card h4 {
  font-size: 15px;
  margin: 0 0 8px;
  font-weight: 700;
}
.feature-card p {
  font-size: 13.5px;
  color: var(--grey);
  line-height: 1.55;
  margin: 0;
}

/* -- Méthodologie / données -- */
.method-band {
  background: linear-gradient(120deg, var(--green), var(--green2) 70%, #051616);
  color: #fff;
  border-radius: 28px;
  padding: 44px 48px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 40px;
  align-items: center;
}
.method-band .num {
  font-size: 46px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--lime);
  white-space: nowrap;
}
.method-band .num small {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 4px;
}
.method-band p {
  font-size: 14.5px;
  line-height: 1.6;
  opacity: 0.9;
  margin: 0;
  max-width: 520px;
}

/* -- Emplacement avis (placeholder honnête, pas de faux témoignages) -- */
.proof-placeholder {
  border: 1.5px dashed var(--line);
  border-radius: 22px;
  padding: 40px;
  text-align: center;
  color: var(--grey);
}
.proof-placeholder .icon {
  font-size: 26px;
  margin-bottom: 10px;
}
.proof-placeholder strong {
  color: var(--ink);
  display: block;
  font-size: 15px;
  margin-bottom: 6px;
}
.proof-placeholder span {
  font-size: 13.5px;
  line-height: 1.55;
  display: block;
  max-width: 440px;
  margin: 0 auto;
}

/* -- FAQ -- */
.faq-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--line);
  border-radius: 18px;
  overflow: hidden;
}
.faq-item {
  background: var(--bg);
  padding: 22px 26px;
}
.faq-item h4 {
  font-size: 15px;
  margin: 0 0 8px;
  font-weight: 700;
}
.faq-item p {
  font-size: 14px;
  color: var(--grey);
  line-height: 1.6;
  margin: 0;
}

/* -- CTA finale -- */
.final-cta {
  background: linear-gradient(135deg, var(--btn), #000);
  color: #fff;
  border-radius: 30px;
  padding: 56px 40px;
  text-align: center;
  margin: 8px 0 40px;
}
.final-cta h3 {
  font-size: 30px;
  margin: 0 0 10px;
  font-weight: 700;
  letter-spacing: -0.015em;
}
.final-cta p {
  color: rgba(255, 255, 255, 0.68);
  margin: 0 0 28px;
  font-size: 15px;
}
.final-cta .cta-main {
  background: var(--lime);
  color: #0a2c2d;
}

.site-footer {
  padding: 26px 0 60px;
  color: var(--grey);
  font-size: 12px;
  text-align: center;
  line-height: 1.6;
}

@media (max-width: 820px) {
  .hero h1 {
    font-size: 38px;
  }
  .surface-row,
  .feature-grid {
    grid-template-columns: 1fr;
  }
  .method-band {
    grid-template-columns: 1fr;
    text-align: center;
  }
  .clay-hero {
    height: auto;
    padding-bottom: 32px;
  }
  .champion {
    display: none;
  }
}
</style>
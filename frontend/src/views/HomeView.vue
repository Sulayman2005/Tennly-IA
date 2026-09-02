<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'

const router = useRouter()

// Carrousel du hero : une photo réelle par surface (dur / terre battue /
// gazon), en écho direct à la section "Couverture" plus bas — purement
// illustratif (aucun joueur, aucun tournoi précis n'est représenté), sous
// licence libre (Pexels). Défilement automatique + navigation manuelle par
// pastille, avec remise à zéro du minuteur sur interaction manuelle.
const slides = [
  {
    key: 'terre',
    label: 'Terre battue',
    place: 'Roland-Garros',
    // Joueur en plein service, court en terre battue, lumière de fin de
    // journée — photo d'action (licence libre Pexels, aucun joueur
    // identifiable/pro réel).
    img: 'https://images.pexels.com/photos/32289805/pexels-photo-32289805.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
  {
    key: 'gazon',
    label: 'Gazon',
    place: 'Wimbledon',
    img: 'https://images.pexels.com/photos/19872965/pexels-photo-19872965.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
  {
    key: 'dur',
    label: 'Dur',
    place: 'US Open · Australian Open',
    // Joueur en pleine frappe, court dur bleu — photo d'action.
    img: 'https://images.pexels.com/photos/33436529/pexels-photo-33436529.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
]
const activeSlide = ref(0)
let slideTimer = null

function scheduleNextSlide() {
  clearInterval(slideTimer)
  slideTimer = setInterval(() => {
    activeSlide.value = (activeSlide.value + 1) % slides.length
  }, 5500)
}

function goToSlide(i) {
  activeSlide.value = i
  scheduleNextSlide()
}

// "Effet wow" d'entrée : le tout premier slide (index 0) reçoit une classe
// .intro-slide le temps d'une entrée en fondu/zoom marquée (voir
// @keyframes heroSlideIntro dans le <style>) — ensuite retirée pour de bon,
// pour laisser place au léger zoom continu (heroKenBurns) sans jamais
// rejouer l'entrée sur les rotations suivantes du carrousel.
const introDone = ref(false)

// Révélation au scroll : même langage visuel (fondu + léger déplacement
// vers le haut) que le hero, mais appliqué au reste de la page au moment où
// chaque bloc entre dans le viewport plutôt qu'au montage du composant —
// sans ça, tout ce qui est sous le premier écran (désormais plein cadre)
// avait déjà fini son animation avant même d'être visible.
const vReveal = {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (typeof binding.value === 'number' && binding.value > 0) {
      el.style.transitionDelay = binding.value + 'ms'
    }
    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add('is-visible')
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            el.classList.add('is-visible')
            io.unobserve(el)
          }
        })
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' },
    )
    io.observe(el)
  },
}

// Chiffres réels de GET /api/stats (backend : HomeStatsSummary/HomeStatsProvider)
// — remplace les valeurs fixes qui étaient codées en dur ici (voir l'ancien
// TODO). `value: null` = pas encore assez de données (même principe "aucune
// donnée inventée" que la page Fiabilité du modèle) : on affiche "—" et on
// n'anime rien, plutôt que d'animer un chiffre inventé. C'est notamment le
// cas aujourd'hui de "Value moyenne" : aucune cote de marché n'est encore
// intégrée côté ml-service (voir le docstring de HomeStatsSummary côté back).
const stats = ref([
  { key: 'successRate', value: null, decimals: 1, prefix: '', suffix: ' %', label: 'Réussite sur 90 jours' },
  { key: 'analyzedMatches', value: null, decimals: 0, prefix: '', suffix: '', label: 'Matchs analysés' },
  { key: 'valueEdge', value: null, decimals: 1, prefix: '+', suffix: ' %', label: 'Value moyenne vs cote de clôture' },
  { key: 'brier', value: null, decimals: 2, prefix: '', suffix: '', label: 'Brier score (plus bas = meilleur)' },
])
const yearsOfHistory = ref(null)
const loading = ref(true)
const loadError = ref(false)

// Icône par stat (purement décoratif) — même convention que les ICONS de
// AdminLayout.vue (map de SVG bruts rendus via v-html), une par clé de
// `stats` ci-dessus plutôt que de réutiliser celles de la grille
// "Fonctionnalités" plus bas, pour éviter qu'un même pictogramme apparaisse
// deux fois sur la page avec un sens différent.
const STAT_ICONS = {
  successRate:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8" stroke="#fff" stroke-width="1.8"/><circle cx="12" cy="12" r="2.6" fill="#fff"/></svg>',
  analyzedMatches:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8" stroke="#fff" stroke-width="1.7"/><path d="M9.3 6.2C11.5 8.6 11.5 15.4 9.3 17.8" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/><path d="M14.7 6.2C12.5 8.6 12.5 15.4 14.7 17.8" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></svg>',
  valueEdge:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 17l6-6 4 4 6-8" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 7h6v6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  brier:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4.5 15a7.5 7.5 0 1115 0" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><path d="M12 15l3.6-4.6" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="15" r="1.3" fill="#fff"/></svg>',
}

// Compteurs et barres animés au chargement (repris du prototype validé) :
// on part de 0 et on anime vers la vraie valeur, plutôt que d'afficher un
// nombre figé d'entrée de jeu. Une stat sans donnée (value === null) n'est
// jamais animée : "—" reste affiché tel quel.
const statValues = ref(stats.value.map(() => 0))
const barWidths = ref(stats.value.map(() => 0))

function formatStat(i) {
  const s = stats.value[i]
  if (s.value === null) return '—'
  return s.prefix + statValues.value[i].toFixed(s.decimals) + s.suffix
}

// Largeur de la barre décorative sous chaque chiffre : purement visuelle
// (pas une donnée affichée en tant que telle), mais dérivée du vrai chiffre
// quand ça a un sens plutôt que d'être une valeur arbitraire.
function barWidthFor(s) {
  if (s.value === null) return 0
  if (s.key === 'successRate') return Math.round(s.value)
  if (s.key === 'brier') return Math.round((1 - s.value) * 100) // plus bas = meilleur -> barre plus pleine
  if (s.key === 'valueEdge') return Math.min(100, Math.round(s.value * 10))
  return 90
}

function animateStats() {
  stats.value.forEach((s, i) => {
    if (s.value === null) return
    const duration = 900
    const start = performance.now()
    function step(now) {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      statValues.value[i] = s.value * eased
      if (t < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  })
  // Décalé d'une frame pour que la transition CSS width parte bien de 0.
  requestAnimationFrame(() => {
    barWidths.value = stats.value.map((s) => barWidthFor(s))
  })
}

const heroSuccessRate = computed(() => {
  const v = stats.value[0].value
  return v !== null ? v.toFixed(1).replace('.', ',') + ' %' : '—'
})
const heroAnalyzedMatches = computed(() => {
  const v = stats.value[1].value
  return v !== null ? new Intl.NumberFormat('fr-FR').format(v) : '—'
})
const heroYearsOfHistory = computed(() => {
  const v = yearsOfHistory.value
  if (v === null) return '—'
  const rounded = Math.round(v)
  return rounded + (rounded > 1 ? ' ans' : ' an')
})

onMounted(async () => {
  try {
    const data = await api.get('/api/stats')
    stats.value[0].value = data.successRateLast90Days
    stats.value[1].value = data.analyzedMatchesCount
    stats.value[2].value = data.averageValueEdgePercent
    stats.value[3].value = data.brierScore
    yearsOfHistory.value = data.yearsOfHistory
  } catch (e) {
    loadError.value = true
  } finally {
    loading.value = false
    animateStats()
  }
  scheduleNextSlide()
  setTimeout(() => {
    introDone.value = true
  }, 1900)
})

onUnmounted(() => {
  clearInterval(slideTimer)
})

function goToMatches() {
  router.push('/matchs')
}

// FAQ en accordéon (un seul item ouvert à la fois) — le premier reste ouvert
// par défaut pour que le format soit immédiatement compris au premier
// affichage, plutôt que de tout présenter fermé.
const faqs = [
  {
    q: 'Tennly IA est-il gratuit ?',
    a: "L'aperçu (favori pressenti + probabilité) est gratuit sur tous les matchs. L'analyse complète — radar comparatif, facteurs d'explication détaillés, cote de valeur — est réservée aux abonnés.",
  },
  {
    q: "Comment fonctionne l'IA ?",
    a: 'Un système Elo par surface combiné à de vraies statistiques de jeu (service, retour, forme, repos), rejoué sur l\'historique ATP réel — pas un modèle opaque qu\'on ne peut pas expliquer.',
  },
  {
    q: 'Est-ce que Tennly IA agit à ma place ?',
    a: "Non. Tennly IA est un outil d'aide à la décision et d'analyse : il ne constitue pas un conseil financier et ne garantit aucun résultat.",
  },
  {
    q: 'Les données sont-elles fiables ?',
    a: "Elles viennent de résultats ATP réellement joués, avec la méthode de calcul documentée publiquement — aucune statistique n'est inventée ou estimée sans le dire.",
  },
]
const openFaqIndex = ref(0)
function toggleFaq(i) {
  openFaqIndex.value = openFaqIndex.value === i ? null : i
}
</script>

<template>
  <!--
    Hero plein cadre : carrousel de 3 vraies photos (terre battue / gazon /
    dur, licence libre Pexels — voir script) en fond, défilement automatique
    + pastilles cliquables. Remplace l'ancien duo "section.hero" (texte sur
    fond blanc) + ".clay-hero" (illustration SVG provisoire) par une seule
    scène immersive : le texte est maintenant surimposé à la photo.
  -->
  <section class="hero-carousel">
    <div
      v-for="(slide, i) in slides"
      :key="slide.key"
      class="hero-slide"
      :class="{ active: i === activeSlide, 'intro-slide': i === 0 && !introDone }"
      :style="{ backgroundImage: `url(${slide.img})`, animationDelay: i * 2 + 's' }"
    ></div>
    <div class="hero-overlay"></div>

    <div class="hero-content">
      <div class="eyebrow"><i></i>IA TENNIS · DONNÉES ATP RÉELLES</div>
      <h1>Prédis chaque <span class="accent">victoire</span><br />avant qu'elle n'ait lieu.</h1>
      <p>Des analyses tennis calibrées par IA, expliquées simplement, avec un historique de performance 100 % public.</p>
      <button class="cta-main" @click="goToMatches">
        Voir les analyses du jour <span class="arrow">→</span>
      </button>
      <div class="hero-stats">
        <div class="hs"><b>{{ heroSuccessRate }}</b> de réussite sur 90 jours</div>
        <div class="hs"><b>{{ heroAnalyzedMatches }}</b> matchs analysés</div>
        <div class="hs"><b>{{ heroYearsOfHistory }}</b> d'historique ATP rejoué</div>
      </div>
    </div>

    <div class="hero-dots" role="tablist" aria-label="Choisir une surface">
      <button
        v-for="(slide, i) in slides"
        :key="'dot-' + slide.key"
        class="hero-dot"
        role="tab"
        :aria-selected="i === activeSlide"
        :class="{ active: i === activeSlide }"
        @click="goToSlide(i)"
      >
        <span class="hero-dot-name">{{ slide.label }}</span>
        <span class="hero-dot-place">{{ slide.place }}</span>
      </button>
    </div>

    <div class="hero-scrollcue" aria-hidden="true"><i></i></div>
  </section>

  <div class="stat-banner">
    <div class="stat-card" v-for="(s, i) in stats" :key="s.label" v-reveal="i * 90">
      <div class="stat-icon" v-html="STAT_ICONS[s.key]"></div>
      <!--
        Le "—" (aucune donnée / pas encore de cote de marché, voir stats
        ci-dessus) passait par le même dégradé de texte que les vrais
        chiffres : un simple tiret rendu en 30px/800 avec ce dégradé
        s'affiche comme une barre pleine sombre, ce qui ressemble à un
        élément cassé plutôt qu'à un texte. Pendant le chargement réel de
        /api/stats (`loading`), on affiche un skeleton animé ; une fois
        chargé, un "—" définitif (valueEdge par ex.) reste du texte simple,
        gris, sans le dégradé.
      -->
      <div class="num" :class="{ 'num-loading': loading, 'num-empty': !loading && s.value === null }">
        <span v-if="loading" class="num-skeleton" aria-hidden="true"></span>
        <template v-else>{{ formatStat(i) }}</template>
      </div>
      <div class="lbl">{{ s.label }}</div>
      <div class="bar"><i :style="{ width: barWidths[i] + '%' }"></i></div>
    </div>
  </div>
  <p v-if="loadError" class="stat-banner-error">
    Impossible de charger les statistiques pour le moment — réessaie un peu plus tard.
  </p>

  <div class="section-divider" aria-hidden="true"><span></span></div>

  <!-- ================= COUVERTURE (surfaces / tournois) ================= -->
  <div class="section">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>COUVERTURE</div>
      <h2>Tous les tournois du circuit ATP, sur toutes les surfaces</h2>
      <p>Le même moteur d'analyse s'adapte à chaque terrain — parce que la terre battue, le dur et le gazon ne se jouent pas pareil.</p>
    </div>
    <div class="surface-row">
      <div class="surface-card dur" v-reveal="0">
        <div class="dot"></div>
        <div class="name">Dur</div>
        <div class="desc">Australian Open, US Open, Masters 1000 indoor/outdoor.</div>
      </div>
      <div class="surface-card terre" v-reveal="110">
        <div class="dot"></div>
        <div class="name">Terre battue</div>
        <div class="desc">Roland-Garros, Monte-Carlo, Rome — l'Elo terre battue tourne à plein régime.</div>
      </div>
      <div class="surface-card gazon" v-reveal="220">
        <div class="dot"></div>
        <div class="name">Gazon</div>
        <div class="desc">Wimbledon et la courte tournée sur herbe qui précède.</div>
      </div>
    </div>
    <div class="level-row" v-reveal="280">
      <span class="level-chip">Grand Chelem</span>
      <span class="level-chip">Masters 1000</span>
      <span class="level-chip">ATP 500</span>
      <span class="level-chip">ATP 250</span>
    </div>
  </div>

  <!-- ================= EXEMPLE CONCRET ================= -->
  <div class="section">
    <div class="section-head" v-reveal>
      <div class="eyebrow"><i></i>CONCRÈTEMENT</div>
      <h2>Voici à quoi ressemble une analyse Tennly IA</h2>
      <p>Une probabilité claire, et surtout les raisons derrière — jamais une boîte noire.</p>
    </div>
    <div class="example-panel">
      <div class="duel" style="margin-bottom: 0; background: transparent" v-reveal>
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
              <circle class="ring-fill" cx="75" cy="75" r="64" stroke-width="14" fill="none" />
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
      <div class="why" style="margin: 22px 0 0; box-shadow: none" v-reveal="120">
        <ul>
          <li><span class="tag ok">✓</span>Elo terre battue en faveur de Sinner (+77 points), recalculé sur l'historique réel de la surface.</li>
          <li><span class="tag ok">✓</span>Dynamique du moment favorable : Elo en progression sur ses 8 derniers matchs.</li>
          <li><span class="tag warn">!</span>Face-à-face équilibré (2 victoires partout) — facteur neutre sur ce match précis.</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="section-divider" aria-hidden="true"><span></span></div>

  <!-- ================= FONCTIONNALITÉS ================= -->
  <div class="section band-soft">
    <div class="band-inner">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>SOUS LE CAPOT</div>
      <h2>Ce que l'IA regarde vraiment</h2>
      <p>Pas de boîte noire : six signaux réels, calculés sur l'historique ATP — rien d'inventé, rien de figé.</p>
    </div>
    <div class="feature-grid">
      <div class="feature-card" v-reveal="0">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 18l5-6 4 4 7-9" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Elo par surface</h4>
        <p>Recalculé match après match sur dur, terre battue et gazon séparément — un joueur peut monter sur l'un et stagner sur l'autre.</p>
      </div>
      <div class="feature-card" v-reveal="70">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8" stroke="#fff" stroke-width="2" />
            <path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Service &amp; retour réels</h4>
        <p>Aces, % de premier service, balles de break — calculés sur les vraies statistiques de jeu, pas une estimation neutre.</p>
      </div>
      <div class="feature-card" v-reveal="140">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 20V10M12 20V4M20 20v-7" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Forme &amp; repos</h4>
        <p>Taux de victoire récent et jours de repos réels avant le match — jamais le résultat du match lui-même.</p>
      </div>
      <div class="feature-card" v-reveal="0">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 4l16 16M20 4L4 20" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Face-à-face</h4>
        <p>L'historique réel entre les deux joueurs, uniquement sur leurs confrontations déjà jouées.</p>
      </div>
      <div class="feature-card" v-reveal="70">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 16l5-9 4 6 3-4 4 6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Dynamique du moment</h4>
        <p>La tendance de l'Elo sur les 8 derniers matchs — un joueur peut progresser même avec un bilan moyen, face à plus fort.</p>
      </div>
      <div class="feature-card" v-reveal="140">
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
  </div>

  <!-- ================= MÉTHODOLOGIE / DONNÉES ================= -->
  <div class="section">
    <div class="method-band" v-reveal>
      <div class="num">4 ans<small>d'historique ATP réel</small></div>
      <p>
        <strong style="color: #fff">Aucune donnée inventée.</strong> Tennly IA rejoue chronologiquement plusieurs années de résultats ATP réels pour
        calculer chaque Elo, chaque score de service et chaque tendance — la méthode est documentée, pas cachée derrière une boîte noire marketing.
      </p>
    </div>
  </div>

  <!-- ================= AVIS (emplacement honnête, pas de faux témoignages) ================= -->
  <div class="section">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>COMMUNAUTÉ</div>
      <h2>Les avis arrivent bientôt</h2>
    </div>
    <div class="proof-placeholder" v-reveal="80">
      <div class="icon">💬</div>
      <strong>Pas encore d'utilisateurs publics</strong>
      <span>Tennly IA vient d'être lancé — dès les premiers retours réels, ils prendront place ici. Aucun avis fictif ne sera jamais affiché à leur place.</span>
    </div>
  </div>

  <!-- ================= FAQ ================= -->
  <div class="section">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>QUESTIONS FRÉQUENTES</div>
      <h2>Tout ce qu'on te demande le plus souvent</h2>
    </div>
    <div class="faq-list">
      <div
        v-for="(faq, i) in faqs"
        :key="faq.q"
        class="faq-item"
        :class="{ open: openFaqIndex === i }"
        v-reveal="i * 60"
      >
        <button type="button" class="faq-question" :aria-expanded="openFaqIndex === i" @click="toggleFaq(i)">
          <span>{{ faq.q }}</span>
          <svg class="faq-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <div class="faq-answer-wrap">
          <div class="faq-answer-inner">
            <p class="faq-answer">{{ faq.a }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="final-cta" v-reveal>
    <h3>Prêt à voir tes premières analyses ?</h3>
    <p>Gratuit à découvrir, sans carte bancaire.</p>
    <button class="cta-main" @click="goToMatches">
      Voir les analyses du jour <span class="arrow">→</span>
    </button>
  </div>

  <div class="site-footer">
    © Tennly IA — Outil d'aide à la décision à titre informatif, ne constitue ni un conseil financier ni une garantie de résultat.
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

/* -- Révélation au scroll (v-reveal) --
   Même langage que le hero (fondu + léger déplacement vers le haut),
   déclenché quand chaque bloc entre dans le viewport (voir vReveal dans le
   <script>) plutôt qu'au montage du composant — pour que tout ce qui est
   sous le hero plein écran s'anime vraiment au fil du scroll, pas juste une
   fois avant même d'être visible. Regroupe ici la transition de transform/
   box-shadow pour les cartes qui ont aussi un effet de survol, afin que les
   deux ne se marchent pas dessus. */
.reveal {
  opacity: 0;
  transform: translateY(26px);
  transition:
    opacity 0.7s cubic-bezier(0.2, 0.8, 0.2, 1),
    transform 0.45s cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 0.3s ease;
}
.reveal.is-visible {
  opacity: 1;
  transform: none;
}

/* -- Hero carrousel --
   Sort volontairement du conteneur `main` (max-width: 1120px, padding
   0 32px — voir App.vue) pour occuper toute la largeur de l'écran, comme un
   vrai fond d'écran plein cadre plutôt qu'une image encadrée au centre de la
   page. Technique classique de "breakout" : on annule le conteneur avec
   100vw + marges négatives calées sur le centre de la fenêtre. */
.hero-carousel {
  position: relative;
  width: 100vw;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  overflow: hidden;
  min-height: calc(100vh - 71px); /* 71px ≈ hauteur du header sticky (App.vue) */
  margin-top: -1px; /* colle au header, sans liseré d'un pixel */
  margin-bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  isolation: isolate;
  animation: fadeUp 0.7s ease both;
}
.hero-slide {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0;
  transition: opacity 1.6s ease;
  animation: heroKenBurns 20s ease-in-out infinite alternate;
  will-change: opacity, transform;
}
.hero-slide.active {
  opacity: 1;
  z-index: 1;
}
@keyframes heroKenBurns {
  from {
    transform: scale(1);
  }
  to {
    transform: scale(1.12);
  }
}
/* Effet "wow" d'entrée : uniquement le tout premier slide, une seule fois
   (voir introDone dans le <script>) — zoom arrière marqué + montée en
   luminosité/saturation, qui se termine pile là où heroKenBurns démarre
   (scale(1), pas de filtre) pour un enchaînement sans à-coup vers la boucle
   continue. */
.hero-slide.active.intro-slide {
  animation:
    heroSlideIntro 1.9s cubic-bezier(0.16, 1, 0.3, 1) both,
    heroKenBurns 20s ease-in-out 1.9s infinite alternate;
}
@keyframes heroSlideIntro {
  from {
    transform: scale(1.26);
    filter: brightness(0.55) saturate(0.75);
  }
  to {
    transform: scale(1);
    filter: brightness(1) saturate(1);
  }
}
.hero-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  /* Voile largement allégé (les photos doivent rester lumineuses et
     lisibles, pas assombries comme un fond de nuit) — juste assez de
     dégradé en bas pour garder le texte/les pastilles lisibles. */
  background:
    linear-gradient(180deg, rgba(6, 14, 13, 0.1) 0%, rgba(5, 12, 12, 0.18) 55%, rgba(4, 9, 9, 0.42) 100%),
    radial-gradient(90% 70% at 50% 0%, rgba(0, 0, 0, 0) 45%, rgba(0, 0, 0, 0.12) 100%);
  animation: heroOverlayIn 2s ease both;
}
@keyframes heroOverlayIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
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
.hero-content {
  position: relative;
  z-index: 3;
  text-align: center;
  max-width: 720px;
  padding: 100px 32px 56px;
}
.hero-content .eyebrow {
  justify-content: center;
  color: var(--lime);
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.35);
  animation: fadeUp 0.6s 0.1s ease both;
}
.hero-content h1 {
  font-size: 58px;
  line-height: 1.05;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0 0 18px;
  color: #fff;
  /* Le voile sombre a été très allégé pour laisser les photos respirer —
     cette ombre légère garde le titre lisible même sur les zones claires
     d'une photo, sans avoir besoin de réassombrir le fond. */
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.45);
  animation: heroTitleIn 1.1s 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes heroTitleIn {
  from {
    opacity: 0;
    transform: translateY(30px);
    filter: blur(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}
.hero-content h1 .accent {
  background: linear-gradient(90deg, var(--lime), #eaffb0);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.hero-content p {
  font-size: 19px;
  color: rgba(255, 255, 255, 0.92);
  max-width: 560px;
  margin: 0 auto 36px;
  text-shadow: 0 1px 12px rgba(0, 0, 0, 0.4);
  animation: fadeUp 0.6s 0.55s ease both;
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
}
.hero-content .cta-main {
  background: var(--lime);
  color: var(--green2);
  animation-delay: 0.75s;
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
  margin: 30px 0 0;
  animation: fadeUp 0.6s 0.95s ease both;
}
.hero-stats .hs {
  display: flex;
  align-items: baseline;
  gap: 7px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.4);
}
.hero-stats .hs b {
  font-size: 20px;
  color: #fff;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.hero-dots {
  position: absolute;
  z-index: 3;
  left: 50%;
  bottom: 26px;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  background: rgba(10, 20, 20, 0.32);
  border: 1px solid rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(10px);
  border-radius: 999px;
  padding: 6px;
  animation: fadeUp 0.6s 1.1s ease both;
}
.hero-dot {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.62);
  border-radius: 999px;
  padding: 9px 16px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.3;
  transition:
    background 0.25s,
    color 0.25s;
}
.hero-dot-place {
  font-size: 10.5px;
  font-weight: 500;
  opacity: 0.75;
}
.hero-dot.active {
  background: #fff;
  color: var(--green2);
}
.hero-dot.active .hero-dot-place {
  opacity: 0.6;
}
.hero-scrollcue {
  position: absolute;
  z-index: 3;
  right: 28px;
  bottom: 30px;
  width: 30px;
  height: 30px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-scrollcue i {
  display: block;
  width: 6px;
  height: 6px;
  border-right: 1.5px solid #fff;
  border-bottom: 1.5px solid #fff;
  transform: rotate(45deg) translateY(-1px);
  animation: scrollcueBounce 1.6s ease-in-out infinite;
}
@keyframes scrollcueBounce {
  0%,
  100% {
    transform: rotate(45deg) translate(-1px, -3px);
    opacity: 0.6;
  }
  50% {
    transform: rotate(45deg) translate(2px, 2px);
    opacity: 1;
  }
}

/* -- Stats -- */
.stat-banner {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 48px 0 60px;
}
.stat-banner-error {
  margin: -44px 0 60px;
  font-size: 13px;
  color: var(--grey);
  text-align: center;
}
.stat-card {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  background: var(--card);
  border-radius: 18px;
  padding: 24px 20px;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: -40%;
  right: -30%;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(199, 255, 60, 0.16), transparent 70%);
  z-index: -1;
}
.stat-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 14px 30px rgba(15, 61, 62, 0.12);
}
.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--green), var(--lime));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}
.stat-card .num {
  min-height: 38px;
  display: flex;
  align-items: center;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  background: linear-gradient(90deg, var(--ink), var(--green2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
/* "—" définitif (pas encore de donnée, ex. value moyenne tant qu'aucune cote
   de marché n'est intégrée) : du texte simple et gris, jamais le dégradé —
   sinon le tiret se rend comme une barre pleine sombre. */
.stat-card .num.num-empty {
  background: none;
  -webkit-background-clip: unset;
  background-clip: unset;
  color: var(--line);
}
.num-skeleton {
  display: inline-block;
  width: 58%;
  max-width: 74px;
  height: 22px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--line) 25%, rgba(15, 61, 62, 0.08) 50%, var(--line) 75%);
  background-size: 200% 100%;
  animation: skeletonShimmer 1.4s ease-in-out infinite;
}
@keyframes skeletonShimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
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

/* -- Séparateur décoratif entre deux sections -- */
.section-divider {
  display: flex;
  justify-content: center;
  padding: 4px 0;
}
.section-divider span {
  width: 46px;
  height: 3px;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--green), var(--lime));
}

/* -- Bande teintée (section Fonctionnalités) --
   Même technique de "breakout" que le hero (100vw + marges négatives) pour
   que le fond dégradé occupe tout l'écran, avec un conteneur interne recalé
   sur le même max-width/padding que `main` (App.vue) pour que le contenu
   reste parfaitement aligné avec le reste de la page. */
.band-soft {
  position: relative;
  width: 100vw;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  background:
    radial-gradient(1100px 420px at 15% 0%, rgba(31, 141, 107, 0.07), transparent 60%),
    radial-gradient(900px 460px at 88% 100%, rgba(199, 255, 60, 0.1), transparent 60%),
    var(--bg, #fff);
}
.band-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 32px;
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
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: 230px;
  border-radius: 18px;
  padding: 22px 22px 20px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  background-size: cover;
  background-position: center;
}
.surface-card::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: linear-gradient(180deg, rgba(10, 20, 20, 0.15) 0%, rgba(6, 12, 12, 0.85) 100%);
  transition: background 0.3s ease;
}
.surface-card:hover {
  transform: translateY(-7px) scale(1.015);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.26);
}
.surface-card.dur {
  background-image: url('https://images.pexels.com/photos/30760348/pexels-photo-30760348.jpeg?auto=compress&cs=tinysrgb&w=1080');
}
.surface-card.terre {
  background-image: url('https://images.pexels.com/photos/30617588/pexels-photo-30617588.jpeg?auto=compress&cs=tinysrgb&w=1080');
}
.surface-card.gazon {
  background-image: url('https://images.pexels.com/photos/19872965/pexels-photo-19872965.jpeg?auto=compress&cs=tinysrgb&w=1080');
}
.surface-card .dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-bottom: 14px;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.25);
}
.surface-card.dur .dot {
  background: #4f8fd1;
}
.surface-card.terre .dot {
  background: var(--clay);
}
.surface-card.gazon .dot {
  background: #6fd17e;
}
.surface-card .name {
  color: #fff;
  font-weight: 700;
  font-size: 17px;
  margin-bottom: 5px;
}
.surface-card .desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.82);
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
  width: 100%;
  height: 100%;
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
  transition: stroke-dashoffset 1.4s cubic-bezier(0.16, 1, 0.3, 1) 0.3s;
}
/* La jauge d'exemple (64 % pour Sinner) reste vide tant que le bloc "duel"
   n'est pas entré dans le viewport (voir v-reveal dans le <script>) — se
   remplit au scroll plutôt que d'afficher un anneau déjà figé au chargement. */
.duel.is-visible .ring-fill {
  stroke-dashoffset: 145;
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
}
.feature-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 34px rgba(15, 61, 62, 0.13);
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
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.feature-card:hover .fi {
  transform: scale(1.1) rotate(-6deg);
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
  border: 1.5px dashed rgba(31, 141, 107, 0.3);
  border-radius: 22px;
  padding: 40px;
  text-align: center;
  color: var(--grey);
  background: radial-gradient(600px 200px at 50% 0%, rgba(199, 255, 60, 0.08), transparent 70%);
}
.proof-placeholder .icon {
  font-size: 26px;
  margin-bottom: 10px;
  display: inline-block;
  animation: gentleBounce 2.4s ease-in-out infinite;
}
@keyframes gentleBounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
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
}
.faq-question {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: none;
  border: none;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  padding: 22px 26px;
}
.faq-question span {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  transition: color 0.2s ease;
}
.faq-chevron {
  flex: none;
  color: var(--grey);
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.faq-item.open .faq-question span {
  color: var(--green);
}
.faq-item.open .faq-chevron {
  transform: rotate(180deg);
  color: var(--green);
}
.faq-answer-wrap {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.35s ease;
}
.faq-item.open .faq-answer-wrap {
  grid-template-rows: 1fr;
}
.faq-answer-inner {
  overflow: hidden;
}
.faq-answer {
  font-size: 14px;
  color: var(--grey);
  line-height: 1.6;
  margin: 0;
  padding: 0 26px 22px;
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
  .hero-content h1 {
    font-size: 36px;
  }
  .hero-content p {
    font-size: 16px;
  }
  .hero-carousel {
    /* En dessous de 820px, le bloc de texte (titre + stats) peut devenir plus
       haut que le carrousel avec ses pastilles positionnées en absolu — elles
       se retrouvaient alors superposées ("1 an d'historique" chevauchait la
       pastille Terre battue/Gazon/Dur). On repasse en flux normal (colonne)
       avec les pastilles après le texte, plutôt qu'en position absolue, pour
       que la hauteur s'adapte toujours au contenu sans jamais se chevaucher. */
    flex-direction: column;
    min-height: 560px;
    padding-bottom: 28px;
  }
  .hero-content {
    padding: 84px 20px 0;
  }
  .hero-dots {
    position: static;
    left: auto;
    bottom: auto;
    transform: none;
    flex-wrap: wrap;
    max-width: calc(100% - 32px);
    justify-content: center;
    margin: 28px auto 0;
  }
  .hero-scrollcue {
    display: none;
  }
  .surface-row,
  .feature-grid {
    grid-template-columns: 1fr;
  }
  .method-band {
    grid-template-columns: 1fr;
    text-align: center;
    padding: 32px 28px;
  }
  .band-inner {
    padding: 0 20px;
  }
  .stat-banner {
    grid-template-columns: 1fr 1fr;
  }
  .duel {
    grid-template-columns: 1fr;
    padding: 28px 24px;
    gap: 20px;
  }
  .mid {
    order: -1;
  }
  .why {
    padding: 24px 22px;
  }
  .section-head h2 {
    font-size: 26px;
  }
}

@media (max-width: 480px) {
  .hero-content h1 {
    font-size: 28px;
  }
  .hero-content {
    padding: 72px 18px 0;
  }
  .hero-stats {
    gap: 16px 22px;
  }
  .hero-dots {
    padding: 5px;
  }
  .hero-dot {
    padding: 7px 12px;
  }
  .band-inner {
    padding: 0 16px;
  }
  .stat-banner {
    grid-template-columns: 1fr;
    margin: 36px 0 48px;
  }
  .section {
    padding: 48px 0;
  }
  .section-head h2 {
    font-size: 22px;
  }
  .section-head p {
    font-size: 14.5px;
  }
  .p-card .av {
    width: 68px;
    height: 68px;
    font-size: 22px;
  }
  .gauge {
    width: 120px;
    height: 120px;
  }
  .method-band {
    padding: 28px 20px;
  }
  .method-band .num {
    font-size: 36px;
  }
  .proof-placeholder {
    padding: 28px 20px;
  }
  .faq-item {
    padding: 18px 20px;
  }
  .final-cta {
    padding: 40px 24px;
    border-radius: 22px;
  }
  .final-cta h3 {
    font-size: 23px;
  }
}
</style>
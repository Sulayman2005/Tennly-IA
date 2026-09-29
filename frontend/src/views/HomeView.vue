<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { api } from '@/api/client'
import { hasPhoto } from '@/utils/playerVisuals'

const router = useRouter()

// Carrousel du hero : une photo par surface (dur / terre battue / gazon), en
// écho direct à la section "Couverture" plus bas. Chaque slide part d'une
// photo d'action générique sous licence libre (Pexels, aucun joueur
// identifiable) — voir SHOWCASE_FALLBACK — et loadShowcaseFavorites() la
// remplace, une fois le composant monté, par un VRAI joueur en tête d'un
// vrai match à venir/en cours sur cette surface (17/09/2026, sur demande
// explicite de mettre en avant "des grosses stars sur des matchs
// importants" en photo). Volontairement PAS de vraie photo d'action de
// presse (Getty/AP, etc. — droits d'auteur bien plus stricts qu'un portrait)
// : on réutilise exactement la même source déjà utilisée partout ailleurs
// sur le site pour les joueurs (portrait Wikipedia via player.photoUrl, voir
// import_player_photos_wikipedia.py) plutôt que d'inventer une photo qu'on
// n'a pas le droit de publier. Si aucun match exploitable n'est trouvé pour
// une surface (creux du calendrier, aucun joueur avec photo…), cette surface
// garde simplement sa photo de secours Pexels — jamais de portrait inventé.
//
// Photos de secours changées le 17/09/2026 (demande explicite) pour des
// prises de vue plus "premium" (drone/aérien, terrains vides, haute
// résolution) — voir aussi le filtre `p.tour === 'atp'` dans
// loadShowcaseFavorites() ci-dessous, qui garantit qu'un vrai joueur mis en
// avant ici est toujours un joueur du circuit ATP (jamais une joueuse WTA),
// sur demande explicite également.
//
// Deuxième passe le 17/09/2026 (toujours sur demande explicite, après retour
// sur le premier choix) : le court "Dur" coincé entre deux immeubles et le
// court "Gazon" au rendu trop sombre ont été remplacés — "Dur" par un
// ensemble de courts bleus en plein jour entouré de verdure (pas de bâtiment
// dans le cadre), "Gazon" par un gros plan lumineux sur les lignes blanches
// d'un vrai gazon (le rendu large de Melbourne posait un problème de
// luminosité). Terre battue inchangée (déjà jugée correcte).
//
// Troisième passe le 29/09/2026 (demande explicite du CEO, "plus premium,
// effet wow" que les courts vides ci-dessus) : d'abord essayé avec 5 captures
// fournies directement par le CEO (photos de tribunes/matchs, hébergées un
// temps dans frontend/public/hero/), puis abandonné sur demande explicite car
// leur provenance/droits n'étaient pas garantis (logos de sponsors visibles).
// Un premier remplacement par des photos d'action génériques sous licence
// libre a ensuite été jugé encore trop plat ("je n'aime pas les images").
// Remplacées ici par des vraies photos d'ambiance de tournoi (Roland-Garros,
// French Open, US Open), toujours sous licence libre Pexels — mêmes
// conditions d'usage que les photos de secours d'origine plus haut — mais
// avec de vrais stades/tribunes pleins plutôt que des courts vides ou une
// action générique, pour se rapprocher de l'effet recherché. Photo "Gazon"
// changée plusieurs fois ensuite sur retours explicites ("pas fade", "en
// grand sur un terrain") — choisie avec le CEO parmi plusieurs propositions,
// finalement une vue aérienne drone sous licence libre Unsplash (même
// principe que Pexels : gratuite, usage commercial autorisé) plutôt que
// Pexels, faute d'y trouver un rendu assez vif. Chargées
// directement depuis le CDN Pexels — pas de copie locale. Terre battue et Dur
// ont chacune 2 photos (2 entrées avec le même `apiSurface`) —
// loadShowcaseFavorites() ci-dessous boucle sur CHAQUE entrée du tableau, pas
// sur chaque surface unique, donc ça fonctionne sans changement à cette
// fonction.
const SHOWCASE_FALLBACK = [
  {
    key: 'terre-1',
    apiSurface: 'terre_battue',
    label: 'Terre battue',
    place: 'Roland-Garros',
    img: 'https://images.pexels.com/photos/26841963/pexels-photo-26841963.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
  {
    key: 'terre-2',
    apiSurface: 'terre_battue',
    label: 'Terre battue',
    place: 'Court en terre battue',
    img: 'https://images.pexels.com/photos/37693849/pexels-photo-37693849.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
  {
    key: 'gazon',
    apiSurface: 'gazon',
    label: 'Gazon',
    place: 'Wimbledon',
    img: 'https://images.unsplash.com/photo-1717869835053-bc3f150e105f?w=1920&fm=jpg&q=80&auto=format&fit=crop',
  },
  {
    key: 'dur-1',
    apiSurface: 'dur',
    label: 'Dur',
    place: 'US Open',
    img: 'https://images.pexels.com/photos/171568/pexels-photo-171568.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
  {
    key: 'dur-2',
    apiSurface: 'dur',
    label: 'Dur',
    place: "Open d'Australie",
    img: 'https://images.pexels.com/photos/29893721/pexels-photo-29893721.jpeg?auto=compress&cs=tinysrgb&w=1920',
  },
]
const slides = ref(SHOWCASE_FALLBACK.map((s) => ({ ...s, player: null })))
const activeSlide = ref(0)
let slideTimer = null

// Vérifie qu'une image se charge vraiment avant de l'utiliser en fond de
// carrousel : contrairement à une balise <img> (qui a déjà un repli visuel
// naturel en cas d'échec), un background-image CSS raté reste simplement
// invisible, sans aucun signal — d'où ce test explicite pour ne jamais
// remplacer une photo de secours qui marche par une URL cassée.
function preloadImage(url) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve(true)
    img.onerror = () => resolve(false)
    img.src = url
  })
}

async function loadShowcaseFavorites() {
  await Promise.all(
    SHOWCASE_FALLBACK.map(async (s, i) => {
      try {
        const data = await api.get(
          `/api/tennis_matches?surface=${s.apiSurface}&status[]=scheduled&status[]=live&order[scheduledAt]=asc&itemsPerPage=15`,
        )
        const matches = data['hydra:member'] ?? data['member'] ?? data
        for (const m of matches) {
          const favorite = m.prediction?.favoritePlayer
          const candidates = favorite ? [favorite, m.playerA, m.playerB] : [m.playerA, m.playerB]
          // tour === 'atp' (sur demande explicite, jamais une joueuse WTA en
          // photo ici) — donnée réelle exposée par l'API (Player::$tour, cf.
          // TourBadge.vue qui s'en sert déjà pour la puce ATP/WTA), jamais
          // devinée.
          const player = candidates.find((p) => p && p.tour === 'atp' && hasPhoto(p))
          if (player && (await preloadImage(player.photoUrl))) {
            slides.value[i] = { ...slides.value[i], img: player.photoUrl, place: m.tournamentName, player: player.fullName }
            return
          }
        }
      } catch {
        // Silencieux : cette surface garde sa photo de secours Pexels.
      }
    }),
  )
}

function scheduleNextSlide() {
  clearInterval(slideTimer)
  slideTimer = setInterval(() => {
    activeSlide.value = (activeSlide.value + 1) % slides.value.length
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

// Compteurs animés "premium" (09/09/2026) : une fois le vrai chiffre reçu de
// /api/stats, il ne s'affiche plus figé d'un coup mais monte en douceur
// depuis 0 — habillage purement visuel de l'ARRIVÉE de la donnée, jamais de
// valeur inventée : la cible de l'animation est toujours exactement la
// valeur réelle de l'API (même logique que "value: null" plus haut — on
// n'anime jamais un chiffre qu'on n'a pas encore). Désactivé pour les
// personnes ayant réduit les animations système (voir prefersReducedMotion),
// qui voient directement la valeur finale sans étape intermédiaire.
function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}
function animateTo(targetRef, finalValue, duration = 1300) {
  if (finalValue === null || finalValue === undefined) return
  if (prefersReducedMotion()) {
    targetRef.value = finalValue
    return
  }
  const start = performance.now()
  function tick(now) {
    const t = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    targetRef.value = finalValue * eased
    if (t < 1) requestAnimationFrame(tick)
    else targetRef.value = finalValue
  }
  requestAnimationFrame(tick)
}
const animSuccessRate = ref(0)
const animAnalyzedMatches = ref(0)

const heroSuccessRate = computed(() => {
  if (stats.value[0].value === null) return '—'
  return animSuccessRate.value.toFixed(1).replace('.', ',') + ' %'
})
const heroAnalyzedMatches = computed(() => {
  if (stats.value[1].value === null) return '—'
  return new Intl.NumberFormat('fr-FR').format(Math.round(animAnalyzedMatches.value))
})

// Halo qui suit le curseur dans le hero (09/09/2026, passe "rendu premium") :
// pur détail d'ambiance, jamais activé au toucher (pas de souris → rien à
// suivre) ni si les animations système sont réduites — voir spotlightEnabled
// et le v-if sur .hero-spotlight dans le template.
const heroSpotlight = reactive({ x: 50, y: 38 })
const spotlightEnabled = ref(false)
function onHeroPointerMove(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  heroSpotlight.x = ((e.clientX - rect.left) / rect.width) * 100
  heroSpotlight.y = ((e.clientY - rect.top) / rect.height) * 100
}

onMounted(async () => {
  spotlightEnabled.value = Boolean(window.matchMedia?.('(pointer: fine)').matches) && !prefersReducedMotion()

  try {
    const data = await api.get('/api/stats')
    stats.value[0].value = data.successRateLast90Days
    stats.value[1].value = data.analyzedMatchesCount
    stats.value[2].value = data.averageValueEdgePercent
    stats.value[3].value = data.brierScore
    // Léger décalage pour démarrer le compteur pile quand .hero-stats entre
    // en scène (animation-delay 0.95s côté CSS) plutôt qu'avant, invisible.
    setTimeout(() => {
      animateTo(animSuccessRate, stats.value[0].value)
      animateTo(animAnalyzedMatches, stats.value[1].value, 1600)
    }, 950)
  } catch (e) {
    // Silencieux : le hero affiche "—" via les computed heroSuccessRate/
    // heroAnalyzedMatches tant que value reste null.
  }
  loadShowcaseFavorites()
  scheduleNextSlide()
  setTimeout(() => {
    introDone.value = true
  }, 1900)
})

// Bandeau défilant "façon Visifoot" sous le hero (17/09/2026, sur demande
// explicite) : uniquement des noms réels de circuits/tournois déjà utilisés
// ailleurs sur cette page (section Couverture plus bas) — pas de vrai logo
// officiel (marque déposée de chaque organisation, droits distincts d'une
// simple mention textuelle) tant qu'on n'a pas d'accord avec ces
// organisations.
//
// Passe "avec les logos" (29/09/2026, sur demande explicite) : toujours pas
// de vraie image de logo protégée (même raison qu'au-dessus — voir aussi le
// commentaire sur .comp-badge plus bas dans ce fichier, qui applique déjà
// exactement ce principe), mais chaque chip a maintenant son propre
// "monogramme" — un rond coloré avec les initiales, dans la couleur
// signature du circuit/tournoi — plutôt qu'un simple texte plat, pour se
// rapprocher visuellement d'un logo sans en reprendre un vrai.
//
// Repasse "encore plus proche d'un vrai logo" (29/09/2026, sur demande
// explicite, le client a choisi cette option plutôt que de fournir ses
// propres fichiers de logos officiels) : le rond devient un écusson à double
// anneau (voir .tour-mono ::after) façon "seal" d'un vrai badge de
// compétition, dans une police condensée façon wordmark. Le libellé à côté du
// rond ATP/WTA ne répète plus le sigle du rond (qui suffisait déjà à
// l'identifier) pour éviter le doublon visuel signalé par le client
// ("ATP ATP").
const tourMarquee = [
  { label: 'Circuit ATP', mono: 'ATP', cls: 'atp' },
  { label: 'Circuit WTA', mono: 'WTA', cls: 'wta' },
  { label: 'Grand Chelem', mono: 'GC', cls: 'gc' },
  { label: 'Australian Open', mono: 'AO', cls: 'ao' },
  { label: 'Roland-Garros', mono: 'RG', cls: 'rg' },
  { label: 'Wimbledon', mono: 'W', cls: 'wm' },
  { label: 'US Open', mono: 'US', cls: 'us' },
  { label: 'Masters 1000', mono: 'M1000', cls: 'm1000' },
]

onUnmounted(() => {
  clearInterval(slideTimer)
})

// Animation de clic sur le bouton principal (16/09/2026, sur demande
// explicite) : au lieu de naviguer instantanément vers /matchs, le bouton
// joue un bref effet de "lancement" (voir .cta-main.launching / @keyframes
// ctaLaunchPulse dans le <style>) pendant ~420ms avant de changer de page —
// assez long pour être visible, assez court pour ne jamais donner
// l'impression que le clic n'a pas fonctionné. `launching` est partagé par
// les deux boutons "Lancer l'analyse" de la page (hero + bandeau final) :
// seul celui réellement cliqué est visible à l'écran au moment du clic.
// Respecte prefers-reduced-motion (déjà utilisé ailleurs dans ce fichier,
// voir prefersReducedMotion) : dans ce cas, navigation immédiate, sans
// délai artificiel ni animation.
const launching = ref(false)
function goToMatches() {
  if (launching.value) return
  if (prefersReducedMotion()) {
    router.push('/matchs')
    return
  }
  launching.value = true
  setTimeout(() => {
    router.push('/matchs')
  }, 420)
}

// FAQ en accordéon (un seul item ouvert à la fois) — le premier reste ouvert
// par défaut pour que le format soit immédiatement compris au premier
// affichage, plutôt que de tout présenter fermé.
const faqs = [
  {
    q: 'Tennly est-il gratuit ?',
    a: "Le favori et ses chances de gagner sont gratuits sur tous les matchs. L'explication complète est réservée aux abonnés.",
  },
  {
    q: 'Comment on devine qui va gagner ?',
    a: "On analyse 6 points importants (niveau sur la surface, forme récente, service, retour, repos, confrontations directes), toujours à partir de vrais matchs déjà joués.",
  },
  {
    q: 'Est-ce que Tennly décide à ma place ?',
    a: "Non. Tennly t'aide à comprendre : ce n'est pas un conseil pour parier de l'argent, et rien n'est garanti.",
  },
  {
    q: 'Est-ce que c\'est vrai, tout ça ?',
    a: "Oui : tout vient de vrais matchs, et on explique comment on calcule, sans rien cacher.",
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
  <section class="hero-carousel" @pointermove="spotlightEnabled && onHeroPointerMove($event)">
    <div
      v-for="(slide, i) in slides"
      :key="slide.key"
      class="hero-slide"
      :class="{ active: i === activeSlide, 'intro-slide': i === 0 && !introDone }"
      :style="{ backgroundImage: `url('${slide.img}')`, animationDelay: i * 2 + 's' }"
    ></div>
    <div class="hero-overlay"></div>
    <div v-if="spotlightEnabled" class="hero-spotlight" :style="{ '--mx': heroSpotlight.x + '%', '--my': heroSpotlight.y + '%' }"></div>

    <div class="hero-content">
      <div class="eyebrow"><i></i>TENNIS · ANALYSE PRO, DONNÉES RÉELLES</div>
      <h1>Analyse et Prédis chaque <span class="accent">Victoire</span></h1>
      <button class="cta-main" :class="{ launching }" @click="goToMatches">
        Lancer l'analyse <span class="arrow">→</span>
      </button>
      <div class="hero-stats">
        <div class="hs"><b>{{ heroSuccessRate }}</b> de pronostics justes ces 3 derniers mois</div>
        <div class="hs"><b>{{ heroAnalyzedMatches }}</b> matchs déjà étudiés</div>
      </div>
    </div>

    <!--
      Navigation du carrousel (29/09/2026) : avec 3 photos, chaque pastille
      pouvait porter son nom + son lieu en toutes lettres sans problème. Avec
      5 photos, ces 5 pastilles à deux lignes de texte deviennent trop larges
      pour tenir sur une ligne (débordement/retour à la ligne moche, y compris
      en desktop). Remplacé par un indicateur compact universel (5 petits
      ronds, celui actif s'allonge en pilule) plus UNE seule légende texte
      au-dessus qui affiche le nom/lieu du slide actif — l'info n'est pas
      perdue, juste affichée une fois au lieu de 5 fois. `:key="activeSlide"`
      sur la légende force Vue à recréer l'élément à chaque changement de
      slide, ce qui relance son animation d'entrée (même technique que les
      fondus déjà utilisés dans cette page). -->
    <div class="hero-nav">
      <p class="hero-nav-caption" :key="activeSlide">
        <span class="hero-nav-caption-name">{{ slides[activeSlide]?.label }}</span>
        <span class="hero-nav-caption-sep" aria-hidden="true"></span>
        <span class="hero-nav-caption-place">{{ slides[activeSlide]?.place }}</span>
      </p>
      <div class="hero-dots" role="tablist" aria-label="Choisir une surface">
        <button
          v-for="(slide, i) in slides"
          :key="'dot-' + slide.key"
          class="hero-dot"
          role="tab"
          :aria-selected="i === activeSlide"
          :aria-label="slide.label + ' — ' + slide.place"
          :class="{ active: i === activeSlide }"
          @click="goToSlide(i)"
        ></button>
      </div>
    </div>

    <div class="hero-scrollcue" aria-hidden="true"><i></i></div>
  </section>

  <!-- ================= COMMENT ÇA MARCHE (09/09/2026) =================
       Section ajoutée sur demande explicite (structure inspirée d'un site
       concurrent) : Tennly n'avait jusqu'ici aucun explicatif "en 3 étapes"
       avant de plonger directement dans la liste des matchs. Les 3 étapes
       reprennent des faits déjà vrais ailleurs sur cette page (6 signaux
       réels — voir la section "Sous le capot" plus bas — et le circuit ATP
       complet — voir .level-row juste en dessous) plutôt que d'inventer un
       nouveau discours.
       Allègement (16/09/2026, sur demande explicite "trop de texte") : plus
       de sous-titre sous le h2, et descriptions des 3 cartes raccourcies en
       une ligne chacune — le ruban animé (.live-ribbon), qui répétait mot
       pour mot les mêmes idées que la section "Sous le capot", a aussi été
       retiré.
       Retour au padding-top standard (29/09/2026) : le modificateur
       .section--tight-top compensait la présence du bandeau de tournois +
       séparateur juste au-dessus (moins d'espace nécessaire par-dessus). Ce
       bandeau a été déplacé plus bas dans la page (voir plus loin) — cette
       section suit donc directement le hero et reprend l'espacement standard
       (.section, 64px) pour ne pas coller au hero. -->
  <div class="section">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>EN 3 ÉTAPES</div>
      <h2>Comment ça marche, Tennly ?</h2>
    </div>
    <div class="steps-row">
      <div class="step-card" v-reveal="0">
        <div class="step-num">1</div>
        <h4>Choisis un match</h4>
        <p>Parmi les matchs en cours et à venir.</p>
      </div>
      <div class="step-arrow" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </div>
      <div class="step-card" v-reveal="90">
        <div class="step-num">2</div>
        <h4>On analyse 6 points importants</h4>
        <p>Sur les dernières 4 années de matchs ATP et WTA déjà joués, récupérés via une API tennis de données privées et publiques confirmées.</p>
        <div class="points-row">
          <span class="point-chip">Niveau sur la surface</span>
          <span class="point-chip">Forme récente</span>
          <span class="point-chip">Service</span>
          <span class="point-chip">Retour</span>
          <span class="point-chip">Repos</span>
          <span class="point-chip">Confrontations directes</span>
        </div>
      </div>
      <div class="step-arrow" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </div>
      <div class="step-card" v-reveal="180">
        <div class="step-num">3</div>
        <h4>On te donne le favori</h4>
        <p>Et les facteurs qui expliquent pourquoi.</p>
      </div>
    </div>
  </div>

  <!-- Bandeau défilant des circuits/tournois (17/09/2026, "façon Visifoot",
       sur demande explicite) — voir tourMarquee dans le script pour le choix
       monogramme coloré plutôt que vrai logo. Liste dupliquée une fois
       ci-dessous pour que la boucle CSS (translateX(-50%)) soit invisible,
       sans saut au raccord.
       Déplacé le 29/09/2026 (sur demande explicite) : il vivait juste après
       le hero, entre le hero et "Comment ça marche" — déplacé ici, entre
       "Comment ça marche" et "Couverture", pour combler le grand espace vide
       qui apparaissait à cet endroit (les deux sections juste au-dessus/
       en-dessous n'ayant chacune que leur propre padding, sans rien entre les
       deux).
       Fond vert retiré + monogrammes ajoutés (29/09/2026, sur demande
       explicite "enlève le fond vert et met les logos") : le bandeau est
       maintenant sur fond blanc, et chaque chip porte un rond coloré avec des
       initiales (voir tourMarquee) au lieu d'un texte plat — même principe
       que .comp-badge plus bas (pas de vraie image de logo protégée, une
       couleur signature à la place). -->
  <div class="tour-ribbon">
    <div class="tour-ribbon-track">
      <span v-for="t in tourMarquee" :key="t.label" class="tour-chip">
        <b class="tour-mono" :class="t.cls">{{ t.mono }}</b>
        {{ t.label }}
      </span>
      <span v-for="t in tourMarquee" :key="t.label + '-dup'" class="tour-chip">
        <b class="tour-mono" :class="t.cls">{{ t.mono }}</b>
        {{ t.label }}
      </span>
    </div>
  </div>

  <div class="section-divider" aria-hidden="true"><span></span></div>

  <!-- ================= COUVERTURE (surfaces / tournois) ================= -->
  <div class="section">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>TOUS LES TERRAINS</div>
      <h2>Toutes les surfaces, tous les grands tournois</h2>
    </div>
    <div class="surface-row">
      <div class="surface-card dur" v-reveal="0">
        <div class="dot"></div>
        <div class="name">Dur</div>
        <div class="desc">Australian Open, US Open.</div>
      </div>
      <div class="surface-card terre" v-reveal="110">
        <div class="dot"></div>
        <div class="name">Terre battue</div>
        <div class="desc">Roland-Garros, Monte-Carlo, Rome.</div>
      </div>
      <div class="surface-card gazon" v-reveal="220">
        <div class="dot"></div>
        <div class="name">Gazon</div>
        <div class="desc">Wimbledon.</div>
      </div>
    </div>
    <!-- "Logos" des compétitions (17/09/2026, sur demande explicite du CEO,
         "façon Visifoot") : pas de vraie image de logo officiel (ATP/Grand
         Chelem) réutilisée ici — on n'a pas les droits sur ces marques
         déposées, contrairement à une photo de terrain générique. À la
         place, un bandeau de "blasons" texte, un par Grand Chelem réel,
         avec la couleur signature de chaque tournoi — même esprit visuel
         qu'un bandeau de logos, sans utiliser de vraie image protégée. -->
    <div class="comp-row" v-reveal="280">
      <span class="comp-badge ao"><b>AO</b>Australian Open</span>
      <span class="comp-badge rg"><b>RG</b>Roland-Garros</span>
      <span class="comp-badge wm"><b>W</b>Wimbledon</span>
      <span class="comp-badge us"><b>US</b>US Open</span>
    </div>
  </div>

  <!-- ================= EXEMPLE CONCRET ================= -->
  <div class="section">
    <div class="section-head" v-reveal>
      <div class="eyebrow"><i></i>PAR EXEMPLE</div>
      <h2>Voici à quoi ressemble une analyse Tennly</h2>
    </div>
    <!-- Restylé en carte sombre le 09/09/2026 (voir .example-panel) : même
         langage visuel que le hero et la carte résultat plutôt qu'un simple
         encart gris clair, avec un petit bandeau "Analyse prête" façon
         aperçu produit. Toujours explicitement présenté comme un exemple
         (voir le titre de section juste au-dessus, et l'étiquette
         ci-dessous), jamais comme un vrai match du jour. -->
    <div class="example-panel">
      <div class="example-tag" v-reveal>
        <span class="example-match">Roland-Garros · Finale (exemple)</span>
        <span class="example-ready"><i></i>C'est prêt !</span>
      </div>
      <div class="duel" style="margin-bottom: 0; background: transparent" v-reveal>
        <div class="p-card">
          <div class="av">JS</div>
          <div class="name">Jannik Sinner</div>
          <div class="rank">N°1 mondial</div>
          <div class="elo">Force sur terre battue : 2 118</div>
        </div>
        <div class="mid">
          <div class="vslabel">CHANCES DE GAGNER</div>
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
          <div class="elo">Force sur terre battue : 2 041</div>
        </div>
      </div>
      <div class="why" v-reveal="120">
        <ul>
          <li><span class="tag ok">✓</span>Sinner est plus fort sur terre battue (+77 points).</li>
          <li><span class="tag ok">✓</span>Il est en pleine forme depuis ses 8 derniers matchs.</li>
          <li><span class="tag warn">!</span>Résultats déjà égaux entre eux (2 victoires chacun) — ça ne change rien.</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="section-divider" aria-hidden="true"><span></span></div>

  <!-- ================= FONCTIONNALITÉS ================= -->
  <div class="section band-soft">
    <div class="band-inner">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>COMMENT ON CALCULE</div>
      <h2>Ce qu'on regarde vraiment</h2>
    </div>
    <div class="feature-grid">
      <div class="feature-card" v-reveal="0">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 18l5-6 4 4 7-9" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>La force de chaque joueur, terrain par terrain</h4>
        <p>Recalculée après chaque match.</p>
      </div>
      <div class="feature-card" v-reveal="70">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="8" stroke="#fff" stroke-width="2" />
            <path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Le service et le retour</h4>
        <p>De vraies statistiques de jeu.</p>
      </div>
      <div class="feature-card" v-reveal="140">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 20V10M12 20V4M20 20v-7" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>La forme et le repos</h4>
        <p>Ses derniers résultats et son temps de repos.</p>
      </div>
      <div class="feature-card" v-reveal="0">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 4l16 16M20 4L4 20" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Leurs matchs l'un contre l'autre</h4>
        <p>Combien de fois ils se sont déjà affrontés, et qui a gagné.</p>
      </div>
      <div class="feature-card" v-reveal="70">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M4 16l5-9 4 6 3-4 4 6" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Sa dynamique du moment</h4>
        <p>Est-ce qu'il progresse ou recule sur ses 8 derniers matchs ?</p>
      </div>
      <div class="feature-card" v-reveal="140">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 3l2.6 6.2L21 10l-5 4.2L17.4 21 12 17.4 6.6 21 8 14.2 3 10l6.4-.8z" stroke="#fff" stroke-width="1.8" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Les surprises</h4>
        <p>Sa capacité à créer l'exploit face à un adversaire mieux classé.</p>
      </div>
    </div>
    </div>
  </div>

  <!-- ================= CHIFFRES CLÉS ================= -->
  <div class="section">
    <!-- Refait le 09/09/2026 (structure inspirée d'un site concurrent, qui
         présente 4 grands chiffres en rangée plutôt qu'un seul). Ancien
         .method-band n'affichait qu'un seul nombre ("3 synchronisations
         automatiques", lui-même un remplacement d'un "X ans d'historique"
         qui sonnait faible — voir l'historique de ce fichier). Il devient
         ici une des 4 cases, aux côtés des deux vrais chiffres déjà utilisés
         dans le hero (réussite/matchs analysés, voir heroSuccessRate/
         heroAnalyzedMatches) et du nombre de signaux réels déjà annoncé
         partout ailleurs sur la page (.live-ribbon, section "Sous le
         capot") — jamais un chiffre inventé pour l'occasion. -->
    <div class="stats-band" v-reveal>
      <div class="stat-cell">
        <div class="stat-num">{{ heroSuccessRate }}</div>
        <div class="stat-label">de pronostics justes ces 3 derniers mois</div>
      </div>
      <div class="stat-cell">
        <div class="stat-num">{{ heroAnalyzedMatches }}</div>
        <div class="stat-label">matchs déjà étudiés</div>
      </div>
      <div class="stat-cell">
        <div class="stat-num">6</div>
        <div class="stat-label">points importants analysés à chaque match</div>
      </div>
      <div class="stat-cell">
        <div class="stat-num">3<small>/nuit</small></div>
        <div class="stat-label">mises à jour automatiques</div>
      </div>
    </div>
  </div>

  <!-- ================= CONFIANCE (16/09/2026, sur demande explicite) =================
       Aucun badge inventé (pas de "10 000 utilisateurs", pas de fausse note
       app store) : les 4 points ci-dessous sont des faits vérifiables du
       site — paiement Stripe déjà en place (voir PaywallModal.vue), page
       /fiabilite déjà publiée avec les vraies statistiques du modèle,
       résiliation "à tout moment" réellement prévue dans les CGV
       (CgvView.vue §"Durée et résiliation"), page /confidentialite déjà
       publiée. Même esprit que le reste de la page : jamais un argument
       qu'on ne peut pas prouver en cliquant dessus. -->
  <div class="section">
    <div class="section-head center" v-reveal>
      <div class="eyebrow" style="justify-content: center"><i></i>CONFIANCE</div>
      <h2>Pourquoi tu peux nous faire confiance</h2>
    </div>
    <div class="trust-grid">
      <div class="trust-item" v-reveal="0">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="5" y="11" width="14" height="9" rx="2" stroke="#fff" stroke-width="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Paiement sécurisé</h4>
        <p>Via Stripe — on ne voit ni ne garde jamais ta carte bancaire.</p>
      </div>
      <div class="trust-item" v-reveal="70">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z" stroke="#fff" stroke-width="2" stroke-linejoin="round" />
            <circle cx="12" cy="12" r="3" stroke="#fff" stroke-width="2" />
          </svg>
        </div>
        <h4>Méthode publique</h4>
        <p><RouterLink :to="{ name: 'model-reliability' }">Voir la fiabilité réelle du modèle →</RouterLink></p>
      </div>
      <div class="trust-item" v-reveal="140">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M3 12a9 9 0 1 0 3-6.7" stroke="#fff" stroke-width="2" stroke-linecap="round" />
            <polyline points="3 4 3 9 8 9" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h4>Résiliable à tout moment</h4>
        <p>Sans engagement, en 2 clics depuis ton compte.</p>
      </div>
      <div class="trust-item" v-reveal="0">
        <div class="fi">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 3l7 3v6c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6l7-3z" stroke="#fff" stroke-width="2" stroke-linejoin="round" />
            <path d="M9 12l2 2 4-4" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          </svg>
        </div>
        <h4>Données protégées</h4>
        <p><RouterLink :to="{ name: 'privacy' }">Conformes au RGPD →</RouterLink></p>
      </div>
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
      <strong>On vient tout juste de commencer</strong>
      <span>Les vrais avis arriveront ici bientôt.</span>
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
    <h3>Prêt à prédire ta première victoire ?</h3>
    <p>C'est gratuit à découvrir, pas besoin de carte bancaire.</p>
    <button class="cta-main" :class="{ launching }" @click="goToMatches">
      Lancer l'analyse <span class="arrow">→</span>
    </button>
  </div>

  <div class="site-footer">
    <div class="footer-legal-links">
      <RouterLink :to="{ name: 'legal-notice' }">Mentions légales</RouterLink>
      <RouterLink :to="{ name: 'cgu' }">CGU</RouterLink>
      <RouterLink :to="{ name: 'cgv' }">CGV</RouterLink>
      <RouterLink :to="{ name: 'privacy' }">Confidentialité</RouterLink>
    </div>
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
/* Passe "rendu premium" (09/09/2026) : léger flou en plus du fondu/
   déplacement, même langage que .hero-content h1 (heroTitleIn) plus haut —
   une "mise au point" progressive plutôt qu'un simple fondu, sur la courbe
   --ease-premium désormais partagée par toute la page. blur() reste léger
   (6px) pour ne pas coûter cher au rendu pendant le scroll. */
.reveal {
  opacity: 0;
  transform: translateY(26px);
  filter: blur(6px);
  transition:
    opacity 0.7s var(--ease-premium),
    transform 0.6s var(--ease-premium),
    filter 0.6s var(--ease-premium),
    box-shadow 0.3s ease;
}
.reveal.is-visible {
  opacity: 1;
  transform: none;
  filter: blur(0);
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
  /* dvh en plus de vh (17/09/2026, demande explicite "prendre tout le
     téléphone") : sur mobile, 100vh ne tient pas toujours compte de la barre
     d'adresse qui apparaît/disparaît au scroll, ce qui peut laisser un peu
     de blanc sous l'image. 100dvh suit la vraie hauteur visible ; navigateurs
     qui ne le supportent pas gardent simplement la valeur vh ci-dessus. */
  min-height: calc(100dvh - 71px);
  /* Revenu à l'ancien comportement (17/09/2026, demande explicite "redescend
     le header à 100vh comme avant") : le header reste solide/opaque en
     permanence (plus de mode transparent flottant sur le hero, voir App.vue),
     donc le hero reprend simplement sa place juste en dessous, sans le
     remonter derrière lui. */
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
  /* Anime aussi la luminosité/saturation en plus du fondu (17/09/2026, sur
     demande explicite "avec des animations") : chaque nouvelle photo se
     "réveille" doucement (un peu terne → pleine couleur) au lieu d'un simple
     fondu plat, en plus du zoom lent continu (heroKenBurns) déjà en place. */
  filter: brightness(0.86) saturate(0.85);
  transition:
    opacity 1.8s ease,
    filter 1.8s ease;
  animation: heroKenBurns 20s ease-in-out infinite alternate;
  will-change: opacity, transform, filter;
}
.hero-slide.active {
  opacity: 1;
  filter: brightness(1) saturate(1);
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
/* Halo qui suit le curseur (09/09/2026, passe "rendu premium") : détail
   d'ambiance discret, jamais rendu si spotlightEnabled est faux côté script
   (tactile ou animations système réduites — voir le v-if dans le template),
   donc jamais de listener pointermove posé pour rien sur mobile. */
.hero-spotlight {
  position: absolute;
  inset: 0;
  z-index: 2;
  background: radial-gradient(480px circle at var(--mx, 50%) var(--my, 38%), rgba(199, 255, 60, 0.16), transparent 62%);
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
}
.hero-carousel:hover .hero-spotlight {
  opacity: 1;
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
  position: relative;
  overflow: hidden;
  isolation: isolate;
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
  /* Passe "rendu premium" : une seule courbe (--ease-premium) et une ombre
     qui se creuse en même temps que le bouton se soulève, plutôt qu'un
     simple scale sans profondeur. */
  transition:
    transform 0.4s var(--ease-premium),
    box-shadow 0.4s var(--ease-premium);
  animation: fadeUp 0.6s 0.2s ease both;
}
.hero-content .cta-main {
  background: var(--lime);
  color: var(--green2);
  animation-delay: 0.75s;
}
/* "Animations sur les boutons" (09/09/2026) : un reflet qui balaie le
   bouton au survol, en plus du soulèvement déjà en place — même idée que
   .result-shine sur la carte résultat de match, réutilisée ici en boucle
   courte déclenchée par :hover plutôt qu'une seule fois au chargement. */
.cta-main::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(100deg, transparent 30%, rgba(255, 255, 255, 0.35) 48%, transparent 66%);
  transform: translateX(-120%);
  pointer-events: none;
}
.cta-main:hover::after {
  animation: ctaShine 0.9s var(--ease-premium);
}
@keyframes ctaShine {
  from {
    transform: translateX(-120%);
  }
  to {
    transform: translateX(120%);
  }
}
.cta-main > * {
  position: relative;
  z-index: 2;
}
.cta-main:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: var(--shadow-elevated);
}
.cta-main:active {
  transform: translateY(-1px) scale(1.005);
  transition-duration: 0.1s;
}
/* Animation de "lancement" au clic (16/09/2026, sur demande explicite) :
   un anneau lumineux part du bouton et s'estompe pendant qu'il se
   comprime puis rebondit légèrement, pendant les ~420ms où la navigation
   vers /matchs est volontairement retardée côté script (voir `launching`/
   goToMatches) pour laisser le temps à l'animation d'être vue. `pointer-
   events: none` évite un double clic pendant que l'animation joue. */
.cta-main.launching {
  animation: ctaLaunchPulse 0.42s var(--ease-premium) both;
  pointer-events: none;
}
@keyframes ctaLaunchPulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(199, 255, 60, 0.55);
  }
  45% {
    transform: scale(0.94);
  }
  100% {
    transform: scale(1.03);
    box-shadow: 0 0 0 24px rgba(199, 255, 60, 0);
  }
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
/* Indicateur du carrousel (29/09/2026, voir commentaire dans le template) :
   conteneur .hero-nav = légende texte du slide actif + rangée de petits
   ronds, groupés et centrés en bas du hero. Volontairement compact (largeur
   totale toujours ~150-180px, quel que soit le nombre de slides) pour ne
   jamais déborder ni s'empiler sur plusieurs lignes, contrairement à
   l'ancienne version avec de grosses pastilles texte. */
.hero-nav {
  position: absolute;
  z-index: 3;
  left: 50%;
  bottom: 26px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: fadeUp 0.6s 1.1s ease both;
}
.hero-nav-caption {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.45);
  white-space: nowrap;
  /* Rejoue à chaque changement de slide grâce au :key côté template — même
     langage de fondu que le reste du hero (fadeUp), en plus discret. */
  animation: heroCaptionIn 0.45s ease both;
}
.hero-nav-caption-place {
  font-weight: 500;
  color: rgba(255, 255, 255, 0.78);
}
.hero-nav-caption-sep {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.55);
  flex: none;
}
@keyframes heroCaptionIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.hero-dots {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(10, 20, 20, 0.32);
  border: 1px solid rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(10px);
  border-radius: 999px;
  padding: 8px;
}
.hero-dot {
  border: none;
  background: rgba(255, 255, 255, 0.38);
  width: 8px;
  height: 8px;
  border-radius: 999px;
  padding: 0;
  cursor: pointer;
  transition:
    width 0.3s ease,
    background 0.3s ease,
    transform 0.2s ease;
}
.hero-dot:hover {
  background: rgba(255, 255, 255, 0.65);
}
.hero-dot.active {
  width: 24px;
  background: var(--lime);
  /* Petit "pop" au changement de photo (17/09/2026, "avec des animations") :
     renforce visuellement que la pastille active vient de changer. */
  transform: scaleY(1.15);
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

/* -- Ruban animé "effet wow" --
   Remplace l'ancien stat-banner à 4 cases, qui dépendait de /api/stats et
   restait vide ou affichait une erreur tant que l'endpoint était lent ou en
   échec. Ici : un ruban défilant en boucle infinie, purement CSS, jamais
   bloqué par un chargement réseau. Sort du conteneur (même technique de
   "breakout" que le hero) pour occuper toute la largeur de l'écran. La liste
   de chips est dupliquée une fois dans le template pour que la boucle
   translateX(-50%) soit invisible (pas de saut au raccord). */
/* Fond vert + halo retirés (29/09/2026, sur demande explicite) : le bandeau
   vit maintenant directement sur le fond blanc de la page, comme la section
   "Couverture" juste après — un masque en dégradé sur les bords (mask-image)
   fait disparaître les chips en douceur plutôt qu'une coupure nette, vu qu'il
   n'y a plus de fond de couleur pour la camoufler. */
.tour-ribbon {
  position: relative;
  width: 100vw;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  overflow: hidden;
  padding: 22px 0;
  margin-top: -1px;
  margin-bottom: 8px;
  mask-image: linear-gradient(90deg, transparent 0, #000 64px, #000 calc(100% - 64px), transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 64px, #000 calc(100% - 64px), transparent 100%);
}
.tour-ribbon-track {
  display: flex;
  width: max-content;
  gap: 14px;
  animation: tourRibbonScroll 26s linear infinite;
}
.tour-ribbon:hover .tour-ribbon-track {
  animation-play-state: paused;
}
@keyframes tourRibbonScroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}
.tour-chip {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 8px 20px 8px 8px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--line);
  color: var(--ink);
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(15, 61, 62, 0.06);
}
/* Monogramme rond coloré (voir commentaire dans le template) : même principe
   que .comp-badge b plus bas dans ce fichier (une couleur "signature" par
   circuit/tournoi, jamais un vrai logo protégé), poussé plus loin (29/09/2026,
   sur demande explicite) façon écusson/"seal" pour se rapprocher visuellement
   d'un vrai logo : double anneau (blanc puis teinté) autour du rond, relief
   intérieur (inset) et légère ombre portée, police condensée en petites
   capitales façon wordmark plutôt qu'un simple aplat de couleur avec du texte
   dessus. --ring fixe la teinte du second anneau, propre à chaque badge. */
.tour-mono {
  --ring: rgba(15, 61, 62, 0.3);
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  padding: 0 7px;
  border-radius: 50%;
  color: #fff;
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: -0.01em;
  flex: none;
  box-shadow:
    0 0 0 2px #fff,
    0 0 0 3px var(--ring),
    inset 0 1px 1px rgba(255, 255, 255, 0.4),
    inset 0 -2px 3px rgba(0, 0, 0, 0.3),
    0 3px 7px rgba(15, 25, 25, 0.16);
}
.tour-mono.atp {
  --ring: rgba(15, 61, 62, 0.35);
  background: linear-gradient(135deg, var(--green), var(--green2));
}
.tour-mono.wta {
  --ring: rgba(166, 55, 124, 0.32);
  background: linear-gradient(135deg, #a6377c, #7a2a5c);
}
.tour-mono.gc {
  --ring: rgba(138, 109, 31, 0.32);
  background: linear-gradient(135deg, #8a6d1f, #4a3b10);
}
.tour-mono.ao {
  --ring: rgba(15, 79, 168, 0.32);
  background: linear-gradient(135deg, #0f4fa8, #1976d2);
}
.tour-mono.rg {
  --ring: rgba(193, 101, 46, 0.32);
  background: linear-gradient(135deg, var(--clay), #b25a2e);
}
.tour-mono.wm {
  --ring: rgba(31, 107, 58, 0.32);
  background: linear-gradient(135deg, #1f6b3a, #2e7d32);
}
.tour-mono.us {
  --ring: rgba(18, 58, 107, 0.32);
  background: linear-gradient(135deg, #123a6b, #1d4e89);
}
.tour-mono.m1000 {
  --ring: rgba(74, 47, 122, 0.32);
  background: linear-gradient(135deg, #4a2f7a, #2c1b4d);
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
/* La transition manquait ici (passe "rendu premium", 09/09/2026) : le
   survol changeait transform/box-shadow instantanément, sans le
   soulèvement fluide qu'on voit partout ailleurs sur la page. */
.surface-card {
  transition:
    transform 0.45s var(--ease-premium),
    box-shadow 0.45s var(--ease-premium);
}
.surface-card:hover {
  transform: translateY(-8px) scale(1.015);
  box-shadow: var(--shadow-elevated);
}
/* Alignées le 17/09/2026 (demande explicite "les mêmes images que sur les
   slides") sur les photos du carrousel du hero (voir SHOWCASE_FALLBACK plus
   haut dans le <script>) — avant, cette section "Tous les terrains" avait
   ses 3 propres photos, jamais mises à jour en même temps que le hero, d'où
   la confusion : les captures partagées montraient CETTE section-ci, pas le
   hero, alors que je ne corrigeais que le hero. */
/* Resynchronisées le 29/09/2026 avec les nouvelles photos du hero (mêmes
   images que la 1re entrée "Terre"/"Dur" du carrousel, voir SHOWCASE_FALLBACK
   plus haut) — décision produit du 17/09/2026 de garder cette section et le
   hero visuellement cohérents, toujours valable. */
.surface-card.dur {
  background-image: url('https://images.pexels.com/photos/171568/pexels-photo-171568.jpeg?auto=compress&cs=tinysrgb&w=1080');
}
.surface-card.terre {
  background-image: url('https://images.pexels.com/photos/26841963/pexels-photo-26841963.jpeg?auto=compress&cs=tinysrgb&w=1080');
}
.surface-card.gazon {
  background-image: url('https://images.unsplash.com/photo-1717869835053-bc3f150e105f?w=1080&fm=jpg&q=80&auto=format&fit=crop');
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
.comp-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  /* Marge verticale ajoutée pour laisser la place au flottement des badges
     (transform translateY) sans que le haut/bas ne soit rogné. */
  padding: 10px 0 14px;
}
.comp-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 8px 8px;
  border-radius: 999px;
  background: var(--card);
  font-size: 12.5px;
  color: var(--grey);
  font-weight: 600;
  border: 1px solid var(--line);
  /* "Flottement" demandé explicitement : chaque badge lévite doucement, à
     son propre rythme (durée/décalage différents par badge ci-dessous) pour
     ne jamais bouger en même temps que ses voisins — plus organique qu'un
     mouvement synchronisé. L'ombre respire en même temps (badgeFloat),
     comme si le badge se soulevait vraiment du fond. */
  animation: badgeFloat 3.6s ease-in-out infinite;
  box-shadow: 0 2px 6px rgba(15, 61, 62, 0.08);
}
@keyframes badgeFloat {
  0%,
  100% {
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(15, 61, 62, 0.08);
  }
  50% {
    transform: translateY(-7px);
    box-shadow: 0 14px 18px -10px rgba(15, 61, 62, 0.22);
  }
}
.comp-badge:nth-child(1) {
  animation-duration: 3.4s;
  animation-delay: 0s;
}
.comp-badge:nth-child(2) {
  animation-duration: 4s;
  animation-delay: -1.1s;
}
.comp-badge:nth-child(3) {
  animation-duration: 3.7s;
  animation-delay: -2.3s;
}
.comp-badge:nth-child(4) {
  animation-duration: 4.3s;
  animation-delay: -0.6s;
}
/* Écusson/"seal" (29/09/2026, sur demande explicite, même passe que
   .tour-mono plus haut dans ce fichier — pour que les deux endroits de la
   page qui montrent ces badges restent visuellement cohérents entre eux) :
   double anneau blanc puis teinté, relief intérieur et légère ombre portée,
   plutôt qu'un simple rond plat — toujours une couleur "signature" par
   tournoi, jamais son vrai logo (voir le commentaire dans le <template>).
   --ring fixe la teinte du second anneau, propre à chaque tournoi. */
.comp-badge b {
  --ring: rgba(15, 61, 62, 0.3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 30px;
  padding: 0 6px;
  border-radius: 50%;
  color: #fff;
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: -0.01em;
  box-shadow:
    0 0 0 2px #fff,
    0 0 0 3px var(--ring),
    inset 0 1px 1px rgba(255, 255, 255, 0.4),
    inset 0 -2px 3px rgba(0, 0, 0, 0.3),
    0 3px 7px rgba(15, 25, 25, 0.16);
}
.comp-badge.ao b {
  --ring: rgba(15, 79, 168, 0.32);
  background: linear-gradient(135deg, #0f4fa8, #1976d2);
}
.comp-badge.rg b {
  --ring: rgba(193, 101, 46, 0.32);
  background: linear-gradient(135deg, var(--clay), #b25a2e);
}
.comp-badge.wm b {
  --ring: rgba(31, 107, 58, 0.32);
  background: linear-gradient(135deg, #1f6b3a, #2e7d32);
}
.comp-badge.us b {
  --ring: rgba(18, 58, 107, 0.32);
  background: linear-gradient(135deg, #123a6b, #1d4e89);
}

/* -- Exemple concret --
   Repensé en carte sombre le 09/09/2026 (voir le commentaire dans le
   <template>) : même langage que le hero et la carte résultat de match,
   avec un halo décoratif (--lime, jamais la couleur de surface d'un match
   réel puisqu'il n'y en a pas ici) plutôt qu'un simple encart gris clair. */
.example-panel {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background: linear-gradient(165deg, #10221f 0%, #050a09 78%);
  border-radius: 26px;
  padding: 10px;
  box-shadow: var(--shadow-elevated);
}
.example-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: radial-gradient(650px 280px at 10% 0%, rgba(199, 255, 60, 0.12), transparent 60%);
}
.example-tag {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding: 18px 24px 6px;
}
.example-match {
  font-size: 12.5px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.58);
  letter-spacing: 0.01em;
}
.example-ready {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--lime);
}
.example-ready i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 0 3px rgba(199, 255, 60, 0.25);
  animation: gentlePulseDot 1.8s ease-in-out infinite;
}
@keyframes gentlePulseDot {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
.duel {
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  gap: 24px;
  align-items: center;
  border-radius: 26px;
  padding: 26px 36px 36px;
  color: #fff;
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
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.08);
}
.p-card.right .av {
  background: var(--blue);
}
.p-card .name {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}
.p-card .rank {
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  margin-top: 4px;
}
.p-card .elo {
  margin-top: 10px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.18);
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-variant-numeric: tabular-nums;
}
.mid {
  text-align: center;
}
.mid .vslabel {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
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
  stroke: rgba(255, 255, 255, 0.14);
}
.gauge .ring-fill {
  stroke: var(--lime);
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
  color: #fff;
}
.gauge .pct span {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}
.why {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 22px;
  padding: 26px 32px 30px;
  margin: 0 10px 10px;
  backdrop-filter: blur(8px);
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
  color: rgba(255, 255, 255, 0.82);
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
  background: rgba(199, 255, 60, 0.18);
  color: var(--lime);
}
.why .tag.warn {
  background: rgba(255, 159, 10, 0.2);
  color: var(--amber);
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
  /* Idem .surface-card ci-dessus : transition ajoutée pour un survol fluide
     plutôt qu'un changement instantané (passe "rendu premium"). */
  transition:
    transform 0.45s var(--ease-premium),
    box-shadow 0.45s var(--ease-premium),
    border-color 0.3s ease;
}
.feature-card:hover {
  transform: translateY(-7px);
  box-shadow: var(--shadow-elevated);
  border-color: transparent;
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

/* -- Confiance (16/09/2026) --
   Même grammaire visuelle que .feature-card (icône en pastille dégradée,
   carte bordée) pour rester cohérent avec le reste de la page, sur 4
   colonnes plutôt que 3 — 4 points de confiance courts et indépendants,
   pas des paragraphes. */
.trust-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.trust-item {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 22px;
  transition:
    transform 0.45s var(--ease-premium),
    box-shadow 0.45s var(--ease-premium),
    border-color 0.3s ease;
}
.trust-item:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-elevated);
  border-color: transparent;
}
.trust-item .fi {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--green), var(--lime));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}
.trust-item h4 {
  font-size: 14.5px;
  margin: 0 0 6px;
  font-weight: 700;
}
.trust-item p {
  font-size: 13px;
  color: var(--grey);
  line-height: 1.5;
  margin: 0;
}
.trust-item p a {
  color: var(--green);
  font-weight: 600;
  text-decoration: none;
}
.trust-item p a:hover {
  text-decoration: underline;
}

/* -- Comment ça marche (09/09/2026) -- */
.steps-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  gap: 18px;
  align-items: stretch;
}
.step-card {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 28px 24px;
  transition:
    transform 0.45s var(--ease-premium),
    box-shadow 0.45s var(--ease-premium),
    border-color 0.3s ease;
}
.step-card:hover {
  transform: translateY(-7px);
  box-shadow: var(--shadow-elevated);
  border-color: transparent;
}
.step-num {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--green), var(--lime));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  margin-bottom: 16px;
  box-shadow: 0 8px 18px rgba(15, 61, 62, 0.3);
}
.step-card h4 {
  font-size: 16px;
  margin: 0 0 8px;
  font-weight: 700;
}
.step-card p {
  font-size: 13.5px;
  color: var(--grey);
  line-height: 1.55;
  margin: 0;
}
.step-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--line);
}

/* -- Les 6 points, directement dans la carte de l'étape 2 (17/09/2026,
   demande explicite : les lister sur ce premier écran, sans avoir à
   descendre plus bas dans la page) -- */
.points-row {
  display: flex;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}
.point-chip {
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--line);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--grey);
}

/* -- Chiffres clés (09/09/2026, remplace l'ancien .method-band à un seul
   chiffre — voir le commentaire dans le <template>) -- */
.stats-band {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background: linear-gradient(120deg, var(--green), var(--green2) 70%, #051616);
  color: #fff;
  border-radius: 28px;
  padding: 44px 40px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 28px;
}
.stats-band::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: radial-gradient(700px 260px at 85% -10%, rgba(199, 255, 60, 0.16), transparent 65%);
}
.stat-cell {
  text-align: center;
}
.stat-num {
  font-size: clamp(28px, 3.2vw, 42px);
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--lime);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.stat-num small {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
  margin-left: 1px;
}
.stat-label {
  margin-top: 9px;
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.4;
}
.stats-note {
  max-width: 720px;
  margin: 22px auto 0;
  text-align: center;
  font-size: 13.5px;
  color: var(--grey);
  line-height: 1.6;
}
.stats-note strong {
  color: var(--ink);
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
  transition: background 0.25s ease;
}
.faq-question:hover {
  background: var(--card);
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
.footer-legal-links {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin-bottom: 12px;
}
.footer-legal-links a {
  color: var(--grey);
  font-weight: 600;
  text-decoration: none;
}
.footer-legal-links a:hover {
  color: var(--ink);
  text-decoration: underline;
}

/* Palier tablette / petit écran de bureau (29/09/2026, sur demande explicite,
   "au format desktop et tablette ça rend pas bien") : jusqu'ici le hero
   n'avait que deux paliers, un desktop "plein écran" (58px de titre) et un
   mobile empilé sous 820px. Sur une largeur intermédiaire (tablette en
   paysage, ou simplement une fenêtre de navigateur pas maximisée sur un
   ordinateur portable), le titre à 58px + le padding desktop laissaient trop
   peu de marge, surtout en hauteur sur un écran de portable. */
@media (max-width: 1180px) and (min-width: 821px) {
  .hero-content h1 {
    font-size: 46px;
  }
  .hero-content {
    padding: 80px 32px 48px;
  }
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
       se retrouvaient alors superposées au texte du hero. On repasse en flux
       normal (colonne) avec les pastilles après le texte, plutôt qu'en
       position absolue, pour que la hauteur s'adapte toujours au contenu
       sans jamais se chevaucher. */
    flex-direction: column;
    min-height: 560px;
    /* Revenu à 28px (17/09/2026) : l'essai à 140px pour repousser le bandeau
       hors du premier écran laissait un grand vide visible au milieu de la
       photo — sur retour explicite ("je préfère comme c'était avant"),
       annulé. */
    padding-bottom: 28px;
  }
  .hero-content {
    /* Remonté un peu (19/09/2026, sur demande explicite) : moins d'espace
       vide au-dessus du titre sur mobile, pour que le texte ne parte pas
       trop bas sur la photo. */
    padding: 60px 20px 0;
  }
  /* Ancienne version (avant le 29/09/2026) : chaque pastille portait son nom
     + son lieu en toutes lettres, ce qui obligeait à gérer ici un retour à
     la ligne (flex-wrap) et un style de pilule par pastille pour rester
     propre une fois empilées. Devenu inutile depuis le passage à .hero-nav
     (légende unique + petits ronds, voir plus haut dans ce fichier) : la
     barre est maintenant assez compacte pour toujours tenir sur une seule
     ligne, à toutes les largeurs. Il ne reste donc plus qu'à la repasser en
     flux normal (elle était en position absolue) puisque le bloc de texte
     peut devenir plus haut que le carrousel sur mobile. */
  .hero-nav {
    position: static;
    left: auto;
    bottom: auto;
    transform: none;
    margin: 24px 0 0;
  }
  .hero-scrollcue {
    display: none;
  }
  .surface-row,
  .feature-grid {
    grid-template-columns: 1fr;
  }
  .trust-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .steps-row {
    grid-template-columns: 1fr;
  }
  .step-arrow {
    transform: rotate(90deg);
    padding: 2px 0;
  }
  .stats-band {
    grid-template-columns: repeat(2, 1fr);
    gap: 26px 16px;
    padding: 32px 24px;
  }
  .band-inner {
    padding: 0 20px;
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
    /* Remonté un peu (19/09/2026), même raison qu'au-dessus (820px). */
    padding: 48px 18px 0;
  }
  .hero-stats {
    gap: 16px 22px;
  }
  .band-inner {
    padding: 0 16px;
  }
  .tour-chip {
    padding: 6px 16px 6px 6px;
    gap: 10px;
    font-size: 12.5px;
  }
  .tour-mono {
    min-width: 32px;
    height: 32px;
    font-size: 10.5px;
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
  .stats-band {
    grid-template-columns: 1fr 1fr;
    padding: 28px 18px;
  }
  .trust-grid {
    grid-template-columns: 1fr;
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

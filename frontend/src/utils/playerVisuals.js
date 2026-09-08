// Logique visuelle partagée pour représenter un joueur/une joueuse sans
// vraie photo (Player.photoUrl reste vide côté backend tant que les droits
// ne sont pas obtenus — voir Player.php) : avatar en dégradé déterministe +
// petit drapeau image, et couleur d'ambiance de carte selon la surface du
// match.
// Utilisé par MatchCard.vue (liste /matchs) et MatchDetailView.vue (fiche
// détaillée) — factorisé ici pour que les deux restent visuellement
// identiques sans dupliquer la palette à deux endroits qui finiraient par
// diverger.

// Initiales façon "maillot" : prénom + nom de famille uniquement (jamais un
// éventuel deuxième prénom), pour rester lisible dans un avatar rond même
// sur les noms à rallonge ("Daniel Adolfo Vallejo" → "DV", pas "DAV").
export function initials(fullName) {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Dégradé d'avatar déterministe par joueur (même joueur = même dégradé
// d'une carte à l'autre, d'une visite à l'autre) : on hache le nom complet
// plutôt que de piocher au hasard, pour que Carlos Alcaraz ait toujours le
// même avatar. Palette resserrée sur des tons "pierre précieuse" proches de
// l'identité existante (teal + lime) pour ne jamais jurer avec le fond des
// cartes, plutôt que des couleurs arbitraires.
const AVATAR_GRADIENTS = [
  ['#1f8a6b', '#c7ff3c'], // signature teal → lime
  ['#0071e3', '#0a2c2d'], // bleu dur → teal foncé
  ['#c1652e', '#f5c451'], // terre battue → or
  ['#6b3fa0', '#d946a0'], // prune → rose
  ['#0a2c2d', '#4fd1c5'], // teal foncé → glace
  ['#2f4858', '#8aa399'], // ardoise → olive
]

function hash(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0
  return Math.abs(h)
}

export function avatarGradient(fullName) {
  const [from, to] = AVATAR_GRADIENTS[hash(fullName) % AVATAR_GRADIENTS.length]
  return { background: `linear-gradient(135deg, ${from}, ${to})` }
}

// Drapeau à partir du code pays (voir Player.php, countryCode) — codes à 3
// lettres façon IOC/ITF, casse non fiable ("USA" vs "usa" selon les
// joueurs), d'où le .toUpperCase(). Volontairement pas de repli par défaut
// pour un code absent de la liste (joueurs russes/biélorusses notamment,
// qui jouent sans drapeau) : pas de drapeau plutôt qu'un mauvais drapeau.
//
// Une vraie petite image (flagcdn.com, alpha-2) plutôt qu'un emoji drapeau :
// Windows ne fournit aucun glyphe pour les emoji drapeau (séquences
// d'indicateurs régionaux) dans Chrome/Edge — testé en conditions réelles,
// ça affichait un rond blanc vide sur la machine Windows du projet. Une image
// s'affiche pareil partout, quel que soit l'OS.
const COUNTRY_ALPHA2 = {
  ESP: 'es', FRA: 'fr', CHN: 'cn', USA: 'us', GER: 'de', ARG: 'ar',
  GBR: 'gb', ITA: 'it', HUN: 'hu', POL: 'pl', BEL: 'be', INA: 'id',
  CZE: 'cz', UKR: 'ua', AUT: 'at', THA: 'th', UZB: 'uz', MON: 'mc',
  PHI: 'ph', KAZ: 'kz', ROU: 'ro', JPN: 'jp', PER: 'pe', NED: 'nl',
  SVK: 'sk', CRO: 'hr', AUS: 'au', SUI: 'ch', CAN: 'ca', BRA: 'br',
  RSA: 'za', SRB: 'rs', SWE: 'se', NOR: 'no', DEN: 'dk', FIN: 'fi',
  GRE: 'gr', POR: 'pt', TUR: 'tr', EGY: 'eg', MAR: 'ma', TUN: 'tn',
  CHI: 'cl', COL: 'co', MEX: 'mx', IND: 'in', KOR: 'kr', TPE: 'tw',
  HKG: 'hk', SGP: 'sg', NZL: 'nz', IRL: 'ie', BUL: 'bg', SLO: 'si',
  SVN: 'si', LAT: 'lv', LTU: 'lt', EST: 'ee', GEO: 'ge', ARM: 'am',
  AZE: 'az', BLR: 'by', RUS: 'ru', ISR: 'il', QAT: 'qa', UAE: 'ae',
  KSA: 'sa', NGA: 'ng', KEN: 'ke', ALG: 'dz', CMR: 'cm', CIV: 'ci',
  SEN: 'sn', PAR: 'py', MDA: 'md', ISL: 'is', LUX: 'lu',
}

export function flagUrl(countryCode) {
  if (!countryCode) return null
  const a2 = COUNTRY_ALPHA2[countryCode.toUpperCase()]
  return a2 ? `https://flagcdn.com/48x36/${a2}.png` : null
}

// Couleur d'ambiance par surface (dur/terre/gazon) : donne à chaque carte
// une identité propre au premier coup d'oeil, tout en restant dans une
// famille de teintes cohérente avec le reste de l'app (--blue et --clay
// existent déjà ailleurs — voir TourBadge.vue et index.html — le vert gazon
// est nouveau, choisi pour rester dans la même caisse de résonance que
// --green/--lime plutôt que d'importer une couleur qui jure).
const SURFACE_ACCENTS = {
  dur: '#0071e3',
  terre: '#c1652e',
  gazon: '#3ea56b',
}

function hexToRgba(hex, alpha) {
  const n = parseInt(hex.slice(1), 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// Variables CSS à poser en :style sur le conteneur (fond dégradé teal +
// halo coloré selon la surface) — voir .match-card (MatchCard.vue) et
// .face-off (MatchDetailView.vue), qui consomment ces variables.
export function surfaceCardVars(surface) {
  const accent = SURFACE_ACCENTS[surface] ?? SURFACE_ACCENTS.gazon
  return {
    '--surface-glow': hexToRgba(accent, 0.32),
    '--surface-shadow': hexToRgba(accent, 0.38),
    '--surface-tint': hexToRgba(accent, 0.16),
  }
}

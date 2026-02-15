// Application ECWM Challenge
let data = null;

// Formatage de date ISO vers français
function formatDateFr(isoDate) {
    if (!isoDate) return null;
    try {
        const date = new Date(isoDate + 'T00:00:00');
        return date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    } catch (e) {
        return isoDate;
    }
}

// Version courte de la date (ex: "17 nov.")
function formatDateShort(isoDate) {
    if (!isoDate) return null;
    try {
        const date = new Date(isoDate + 'T00:00:00');
        return date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'short'
        });
    } catch (e) {
        return isoDate;
    }
}

// Charger les données au démarrage
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupTabs();
});

// Chargement des données
async function loadData() {
    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Erreur de chargement');

        data = await response.json();
        hideLoading();
        renderPage();
    } catch (error) {
        showError();
        console.error('Erreur:', error);
    }
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('content').style.display = 'block';
}

function showError() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').style.display = 'block';
}

// Render complet de la page
function renderPage() {
    // Header
    document.getElementById('lastUpdate').textContent =
        `Dernière mise à jour : ${data.meta.derniere_maj}`;

    // Tabs
    renderClassement();
    renderBareme();
    renderBadgesTab();
    renderCourses();
}

// === TAB: CLASSEMENT ===

function renderClassement() {
    const podiumEl = document.getElementById('podium');
    const classementEl = document.getElementById('classement');

    // Podium dans l'ordre classique : 2ème, 1er, 3ème
    const top3 = data.coureurs.slice(0, 3);
    if (top3.length >= 3) {
        podiumEl.innerHTML = [top3[1], top3[0], top3[2]].map(coureur => `
            <div class="podium-item rank-${coureur.rang}">
                <div class="podium-medal">${getMedal(coureur.rang)}</div>
                <div class="podium-name">${coureur.nom}</div>
                <div class="podium-points">${coureur.points_total} pts</div>
            </div>
        `).join('');
    } else {
        // Si moins de 3 coureurs, affichage simple
        podiumEl.innerHTML = top3.map(coureur => `
            <div class="podium-item rank-${coureur.rang}">
                <div class="podium-medal">${getMedal(coureur.rang)}</div>
                <div class="podium-name">${coureur.nom}</div>
                <div class="podium-points">${coureur.points_total} pts</div>
            </div>
        `).join('');
    }

    // Classement complet (du 1er au dernier)
    classementEl.innerHTML = data.coureurs.map(coureur => `
        <div class="coureur-item" data-coureur="${coureur.nom}">
            <div class="coureur-header" onclick="toggleCoureur(this)">
                <div class="coureur-rank">${coureur.rang}.</div>
                <div class="coureur-name">${coureur.nom}</div>
                ${coureur.badges && coureur.badges.length > 0 ? `
                    <div class="badges-compact">
                        ${renderBadgesCompact(coureur.badges)}
                    </div>
                ` : ''}
                <div class="coureur-courses-badge">${coureur.nb_courses}</div>
                <div class="coureur-points">${coureur.points_total}</div>
                <div class="expand-icon">▶</div>
            </div>
            <div class="coureur-details">
                ${renderCoureurDetails(coureur)}
            </div>
        </div>
    `).join('');
}

function toggleCoureur(element) {
    const item = element.closest('.coureur-item');
    item.classList.toggle('expanded');
}

function renderCoureurDetails(coureur) {
    if (coureur.courses_detail.length === 0) {
        return '<p class="text-muted">Aucune course pour le moment</p>';
    }

    return `
        <div>
            ${coureur.badges && coureur.badges.length > 0 ? `
                <div style="margin-bottom: 1.5rem;">
                    <strong>Badges obtenus (${coureur.badges.length})</strong>
                    <div class="badges-detailed">
                        ${renderBadgesWithProgress(coureur.badges, coureur)}
                    </div>
                </div>
            ` : ''}
            
            <strong>Détail des courses (${coureur.courses_detail.length})</strong>
            <table class="courses-table">
                <thead>
                    <tr>
                        <th>Course</th>
                        <th>Position</th>
                        <th>Points</th>
                    </tr>
                </thead>
                <tbody>
                    ${coureur.courses_detail
                        .slice()
                        .sort((a, b) => {
                            // Trier par date décroissante
                            const dateA = a.date_course || '0000-00-00';
                            const dateB = b.date_course || '0000-00-00';
                            return dateB.localeCompare(dateA);
                        })
                        .map(course => `
                        <tr>
                            <td class="${course.bonus_objectif > 1 || course.echelon ? 'course-objectif' : ''}">
                                ${(() => {
                                    const icons = [];
                                    if (course.bonus_objectif > 1) icons.push('⭐');
                                    if (course.echelon === 'national') icons.push('🇫🇷');
                                    if (course.echelon === 'international') icons.push('🌍');
                                    const prefix = icons.length ? icons.join('') + ' ' : '';
                                    const name = course.course.toUpperCase();
                                    return icons.length
                                        ? `<strong>${prefix}${name}</strong>`
                                        : `<strong>${name}</strong>`;
                                })()}<br>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">
                                    ${course.date_course ? formatDateShort(course.date_course) + ' - ' : ''}${course.discipline.toUpperCase()} ${course.federation.toUpperCase()}
                                </span>
                            </td>
                            <td>
                                <strong>${course.position}/${course.nb_participants}</strong><br>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">
                                    ${course.percentile}%
                                </span>
                            </td>
                            <td>
                                <strong style="font-size: 1.125rem;">${course.points}</strong><br>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">
                                    (${course.bonus_participation ? (() => {
                                        const labels = [];
                                        if (course.bonus_objectif > 1) labels.push('objectif club');
                                        if (course.bonus_echelon > 1) labels.push(`échelon ${course.echelon}`);
                                        const title = `Bonus participation (${labels.join(' + ')})`;
                                        return `<span style="color: #16a34a; font-weight: 600; text-decoration: line-through;">${course.points_participation_base}</span> <span style="color: #16a34a; font-weight: 600;" title="${title}">${course.points_participation}</span>`;
                                    })() : course.points_participation} + ${course.points_perf_reduits ?
                                        `<span style="color: #E60017; font-weight: 600; text-decoration: line-through;">${course.points_performance_base}</span> <span style="color: #E60017; font-weight: 600;" title="Points de performance réduits (petite course)">${course.points_performance}</span>`
                                        :
                                        course.points_performance
                                    })
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            ${(() => {
                const totParticipation = Math.round(coureur.courses_detail.reduce((s, c) => s + c.points_participation, 0));
                const totPerformance = Math.round(coureur.courses_detail.reduce((s, c) => s + c.points_performance, 0));
                return `
                <div style="margin-top: 1rem; padding: 0.75rem; background: var(--bg); border-radius: 0.5rem;">
                    <strong>Total des points :</strong><br>
                    <div style="margin-top: 0.5rem; font-size: 1rem; color: var(--text-muted);">
                        ${totParticipation} pts participation<br>
                        + ${totPerformance} pts performance
                        <hr style="margin: 0.5rem 0; border: none; border-top: 1px solid var(--border);">
                        = ${coureur.points_courses} pts (courses)
                        ${coureur.bonus_badges > 0 ? `<br>+ ${coureur.bonus_badges} pts (badges)` : ''}
                        <hr style="margin: 0.5rem 0; border: none; border-top: 2px solid var(--border);">
                        <strong style="color: var(--accent); font-size: 1.5rem;">${coureur.points_total} pts</strong>
                    </div>
                </div>`;
            })()}
        </div>
    `;
}

function getMedal(rang) {
    const medals = { 1: '🥇', 2: '🥈', 3: '🥉' };
    return medals[rang] || '';
}

function renderBadgesCompact(badges) {
    if (!badges || badges.length === 0) return '';
    
    return badges.map(badge => {
        const niveau = badge.niveau || 'unique';
        const niveauClass = niveau.toLowerCase();
        return `<span class="badge-emoji niveau-${niveauClass}" title="${badge.nom}${badge.niveau ? ' ' + badge.niveau : ''}">${badge.emoji}</span>`;
    }).join('');
}

function renderBadgesWithProgress(badges, coureur) {
    if (!badges || badges.length === 0) return '';
    
    // Calculer les stats du coureur pour les barres de progression
    const stats = {
        nb_courses: coureur.nb_courses,
        nb_podiums: coureur.courses_detail.filter(c => parseInt(c.position) <= 3).length,
        nb_top10: coureur.courses_detail.filter(c => parseInt(c.position) <= 10).length
    };
    
    return badges.map(badge => {
        const niveau = badge.niveau || 'unique';
        const niveauClass = niveau.toLowerCase();
        
        // Chercher le palier suivant pour les badges à paliers
        let nextLevel = null;
        if (badge.niveau && data.badges_config) {
            const badgesFamily = data.badges_config.filter(b => b.nom === badge.nom && b.type === 'palier');
            badgesFamily.sort((a, b) => a.seuil - b.seuil);
            
            const currentIndex = badgesFamily.findIndex(b => b.niveau === badge.niveau);
            if (currentIndex >= 0 && currentIndex < badgesFamily.length - 1) {
                nextLevel = badgesFamily[currentIndex + 1];
            }
        }
        
        const bonusText = badge.bonus_points > 0 ? ` <span class="badge-bonus">+${badge.bonus_points} pts</span>` : '';
        
        let progressBar = '';
        if (nextLevel) {
            let currentValue = 0;
            let label = '';
            
            // Déterminer la valeur actuelle selon le type de badge
            if (badge.badge_id.includes('assidu')) {
                currentValue = stats.nb_courses;
                label = 'course';
            } else if (badge.badge_id.includes('podium')) {
                currentValue = stats.nb_podiums;
                label = 'podium';
            } else if (badge.badge_id.includes('top10')) {
                currentValue = stats.nb_top10;
                label = 'top 10';
            }
            
            if (currentValue > 0 || label) {
                const progress = (currentValue / nextLevel.seuil) * 100;
                const remaining = nextLevel.seuil - currentValue;
                const nextBonus = nextLevel.bonus_points > 0 ? ` (+${nextLevel.bonus_points})` : '';
                progressBar = `
                    <div class="badge-progress">
                        <div class="progress-bar-container">
                            <div class="progress-bar-enhanced">
                                <div class="progress-fill-enhanced" style="width: ${Math.min(progress, 100)}%">
                                    <span class="progress-current-value">${currentValue}</span>
                                </div>
                                <div class="progress-empty-enhanced">
                                    ${remaining > 0 ? `<span class="progress-remaining-value">+${remaining}</span>` : ''}
                                </div>
                            </div>
                            <div class="progress-target-label">
                                → ${nextLevel.niveau}${nextBonus}
                            </div>
                        </div>
                    </div>
                `;
            }
        }
        
        // Si progressBar, description inline. Sinon, description en dessous.
        const hasProgress = progressBar !== '';

        return `
            <div class="badge-item">
                <span class="badge-emoji-large niveau-${niveauClass}">${badge.emoji}</span>
                <div class="badge-info-detailed">
                    <div class="badge-name-line">
                        <strong>${badge.nom}</strong>
                        ${badge.niveau ? `<span class="badge-level niveau-${niveauClass}">${badge.niveau}</span>` : ''}
                        ${hasProgress ? `<span class="badge-desc-inline"> — ${badge.description}</span>` : ''}
                        ${bonusText}
                    </div>
                    ${!hasProgress ? `<div class="badge-desc">${badge.description}</div>` : ''}
                    ${progressBar}
                </div>
            </div>
        `;
    }).join('');
}

function renderBadges(badges, compact = false) {
    if (!badges || badges.length === 0) return '';

    return badges.map(badge => {
        const niveau = badge.niveau || 'Unique';
        const niveauClass = niveau.toLowerCase();
        const bonusText = badge.bonus_points > 0 ? ` (+${badge.bonus_points} pts)` : '';
        const tooltipText = `${badge.description}${badge.niveau ? ` (${badge.niveau})` : ''}${bonusText}`;

        return `
            <span class="badge niveau-${niveauClass}" title="${tooltipText}">
                <span class="badge-emoji">${badge.emoji}</span>
                ${!compact ? `<span class="badge-nom">${badge.nom}</span>` : ''}
                ${!compact && badge.niveau ? `<span class="badge-niveau">${badge.niveau}</span>` : ''}
                ${!compact && badge.bonus_points > 0 ? `<span class="badge-bonus">+${badge.bonus_points}</span>` : ''}
            </span>
        `;
    }).join('');
}

// === TAB: BAREME ===

function renderBareme() {
    // Paramètres
    document.getElementById('ptsParticipation').textContent =
        `${data.config.points_participation} pts`;
    document.getElementById('ptsPerformanceMax').textContent =
        data.config.points_performance_max;
    document.getElementById('bonusObjectif').textContent =
        data.config.bonus_objectif;
    document.getElementById('bonusEchelonNational').textContent =
        data.config.bonus_echelon_national;
    document.getElementById('bonusEchelonInternational').textContent =
        data.config.bonus_echelon_international;

    // Paliers de réduction (points de performance)
    const paliersEl = document.getElementById('paliersReduction');
    if (paliersEl && data.paliers_reduction && data.paliers_reduction.length > 0) {
        let html = '<p style="color: #E60017; font-weight: 600; margin-bottom: 0.5rem;">⚠️ Réduction sur les petites courses :</p>';
        html += '<ul style="margin: 0; padding-left: 1.5rem;">';
        data.paliers_reduction.forEach(palier => {
            if (palier.coefficient_reduction >= 1) return; // Ne montrer que les réductions
            const range = `${palier.nb_participants_min}–${palier.nb_participants_max} participants`;
            const percent = Math.round(palier.coefficient_reduction * 100);
            html += `<li>${range} : ${percent}% des points de performance</li>`;
        });
        html += '</ul>';
        paliersEl.innerHTML = html;
    }
}

// === TAB: BADGES ===

function renderBadgesTab() {
    if (!data.badges_config || data.badges_config.length === 0) {
        document.getElementById('badgesPaliers').innerHTML = '<p>Aucun badge configuré</p>';
        document.getElementById('badgesUniques').innerHTML = '';
        return;
    }

    // Séparer badges à paliers et badges uniques
    const badgesPaliers = {};
    const badgesUniques = [];

    data.badges_config.forEach(badge => {
        if (badge.type === 'palier') {
            if (!badgesPaliers[badge.nom]) {
                badgesPaliers[badge.nom] = [];
            }
            badgesPaliers[badge.nom].push(badge);
        } else {
            badgesUniques.push(badge);
        }
    });

    // Render badges à paliers
    const paliersEl = document.getElementById('badgesPaliers');
    let paliersHtml = '';

    for (const [nom, badges] of Object.entries(badgesPaliers)) {
        // Trier par seuil croissant
        badges.sort((a, b) => a.seuil - b.seuil);

        const emoji = badges[0].emoji;
        const description = badges[0].description;
        const critere = getCritereLabel(badges[0].critere);

        paliersHtml += `
            <div class="badge-explanation">
                <div class="badge-header">
                    <div class="badge-icon">${emoji}</div>
                    <div class="badge-info">
                        <h4>${nom}</h4>
                        <div class="badge-levels">
                            ${badges.map(b => `
                                <span class="badge-level ${b.niveau.toLowerCase()}">
                                    ${b.niveau} (${b.seuil}${getCritereUnit(b.critere)})
                                </span>
                            `).join('')}
                        </div>
                    </div>
                </div>
                <p class="badge-description">${description}</p>
                <div class="badge-details">
                    <div class="badge-detail">
                        <span class="badge-detail-label">Critère</span>
                        <span class="badge-detail-value">${critere}</span>
                    </div>
                    <div class="badge-detail">
                        <span class="badge-detail-label">Points bonus</span>
                        <span class="badge-detail-value bonus">
                            ${badges.map(b => `${b.niveau}: +${b.bonus_points}`).join(' • ')}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }

    paliersEl.innerHTML = paliersHtml;

    // Render badges uniques
    const uniquesEl = document.getElementById('badgesUniques');
    let uniquesHtml = '';

    badgesUniques.forEach(badge => {
        const critere = getCritereLabel(badge.critere);
        const seuil = badge.seuil < 100 ? badge.seuil + getCritereUnit(badge.critere) : '';

        uniquesHtml += `
            <div class="badge-explanation">
                <div class="badge-header">
                    <div class="badge-icon">${badge.emoji}</div>
                    <div class="badge-info">
                        <h4>${badge.nom}</h4>
                    </div>
                </div>
                <p class="badge-description">${badge.description}</p>
                <div class="badge-details">
                    <div class="badge-detail">
                        <span class="badge-detail-label">Condition</span>
                        <span class="badge-detail-value">${critere}${seuil ? ': ' + seuil : ''}</span>
                    </div>
                    ${badge.bonus_points > 0 ? `
                        <div class="badge-detail">
                            <span class="badge-detail-label">Points bonus</span>
                            <span class="badge-detail-value bonus">+${badge.bonus_points} pts</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    uniquesEl.innerHTML = uniquesHtml;
}

function getCritereLabel(critere) {
    const labels = {
        'nb_courses': 'Nombre de courses',
        'nb_courses_objectif': 'Courses objectif',
        'nb_podiums': 'Podiums (top 3)',
        'nb_top10': 'Top 10',
        'nb_abandons': 'Abandons',
        'deux_disciplines': 'Route ET (CX ou VTT)',
    };
    return labels[critere] || critere;
}

function getCritereUnit(critere) {
    if (critere === 'percentile_moyen' || critere === 'taux_participation') {
        return '%';
    }
    return '';
}

// === TAB: COURSES ===

const courseFilters = {
    disciplines: new Set(),
    federations: new Set(),
    objectifOnly: false,
    hidePassed: true,
    sortAsc: true,
};

function renderCourses() {
    const coursesEl = document.getElementById('listeCourses');
    const disciplines = [...new Set(data.courses.map(c => c.discipline))].sort();
    courseFilters.disciplines = new Set(disciplines);
    const federations = [...new Set(data.courses.map(c => c.federation))].sort();
    courseFilters.federations = new Set(federations);

    coursesEl.innerHTML = `
        <div class="courses-filters">
            <div class="filter-group">
                ${disciplines.map(d => `
                    <div class="filter-chip active" data-disc="${d}">${d.toUpperCase()}</div>
                `).join('')}
            </div>
            <div class="filter-group">
                ${federations.map(f => `
                    <div class="filter-chip active" data-fede="${f}">${f.toUpperCase()}</div>
                `).join('')}
            </div>
            <div class="filter-group">
                <div class="filter-chip" id="chipObjectif">⭐ Objectifs club</div>
                <div class="filter-chip active" id="chipPassed">📅 Masquer les courses passées</div>
            </div>
        </div>
        <div id="coursesTableContainer"></div>
    `;

    // Discipline chips
    coursesEl.querySelectorAll('[data-disc]').forEach(chip => {
        chip.addEventListener('click', () => {
            const d = chip.dataset.disc;
            if (courseFilters.disciplines.has(d)) {
                courseFilters.disciplines.delete(d);
                chip.classList.remove('active');
            } else {
                courseFilters.disciplines.add(d);
                chip.classList.add('active');
            }
            applyCourseFilters();
        });
    });

    // Federation chips
    coursesEl.querySelectorAll('[data-fede]').forEach(chip => {
        chip.addEventListener('click', () => {
            const f = chip.dataset.fede;
            if (courseFilters.federations.has(f)) {
                courseFilters.federations.delete(f);
                chip.classList.remove('active');
            } else {
                courseFilters.federations.add(f);
                chip.classList.add('active');
            }
            applyCourseFilters();
        });
    });

    document.getElementById('chipObjectif').addEventListener('click', () => {
        courseFilters.objectifOnly = !courseFilters.objectifOnly;
        document.getElementById('chipObjectif').classList.toggle('active-accent', courseFilters.objectifOnly);
        applyCourseFilters();
    });

    document.getElementById('chipPassed').addEventListener('click', () => {
        courseFilters.hidePassed = !courseFilters.hidePassed;
        document.getElementById('chipPassed').classList.toggle('active', courseFilters.hidePassed);
        applyCourseFilters();
    });

    applyCourseFilters();
}

function applyCourseFilters() {
    const today = new Date().toISOString().split('T')[0];

    const filtered = data.courses.filter(c => {
        if (!courseFilters.disciplines.has(c.discipline)) return false;
        if (!courseFilters.federations.has(c.federation)) return false;
        if (courseFilters.objectifOnly && !c.is_objectif) return false;
        if (courseFilters.hidePassed && c.date_course && c.date_course <= today) return false;
        return true;
    });

    const coursesArray = filtered.slice().sort((a, b) => {
        const dateA = a.date_course || (courseFilters.sortAsc ? '9999-12-31' : '0000-00-00');
        const dateB = b.date_course || (courseFilters.sortAsc ? '9999-12-31' : '0000-00-00');
        const cmp = dateA.localeCompare(dateB) || a.nom.localeCompare(b.nom);
        return courseFilters.sortAsc ? cmp : -cmp;
    });

    const container = document.getElementById('coursesTableContainer');
    if (coursesArray.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); padding: 1rem 0;">Aucune course à afficher.</p>';
        return;
    }

    const arrow = courseFilters.sortAsc ? ' ▲' : ' ▼';
    const rows = coursesArray.map(course => {
        const icons = [];
        if (course.is_objectif) icons.push('⭐');
        if (course.echelon === 'national') icons.push('🇫🇷');
        if (course.echelon === 'international') icons.push('🌍');
        const prefix = icons.length ? icons.join('') + ' ' : '';
        const name = course.nom.toUpperCase();
        const nameHtml = icons.length ? `<strong>${prefix}${name}</strong>` : `<strong>${name}</strong>`;

        const discHtml = `<span class="discipline-badge">${course.discipline.toUpperCase()} ${course.federation.toUpperCase()}</span>`;

        const dateHtml = course.date_course
            ? `<span style="white-space: nowrap;">${formatDateShort(course.date_course)}</span>`
            : '<span style="color: var(--text-muted);">—</span>';

        const clubHtml = course.nb_participants > 0
            ? `<strong>${course.nb_participants}</strong> coureur${course.nb_participants > 1 ? 's' : ''}`
            : '<span style="color: var(--text-muted);">—</span>';

        return `
            <tr>
                <td>${dateHtml}</td>
                <td>${nameHtml}<br><span style="font-size: 0.75rem; color: var(--text-muted);">${discHtml}</span></td>
                <td style="text-align: right;">${clubHtml}</td>
            </tr>
        `;
    }).join('');

    container.innerHTML = `
        <table class="courses-table">
            <thead>
                <tr>
                    <th class="sortable" id="sortDate">Date${arrow}</th>
                    <th>Course</th>
                    <th style="text-align: right;">Participants club</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;

    document.getElementById('sortDate').addEventListener('click', () => {
        courseFilters.sortAsc = !courseFilters.sortAsc;
        applyCourseFilters();
    });
}

// === TABS NAVIGATION ===

function setupTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Retirer active de tous
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));

            // Activer celui cliqué
            tab.classList.add('active');
            const tabName = tab.dataset.tab;
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });
}

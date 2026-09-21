(function () {
	var buttons = document.querySelectorAll('.tab-btn');
	var panels = document.querySelectorAll('.tab-panel');
	var titles = {
		tabelle: 'Reserve-Superleague - Tabelle',
		spiele: 'Reserve-Superleague - Spiele',
		torschuetzen: 'Reserve-Superleague - Torschützen'
	};
	var WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];

	function formatDate(isoDate) {
		var parts = isoDate.split('-');
		var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
		return WEEKDAYS[d.getDay()] + ', ' + parts[2] + '.' + parts[1] + '.' + parts[0];
	}

	function renderGames(data) {
		var tbody = document.getElementById('spiele-body');
		if (!tbody || !data || !data.rounds || !data.rounds.length) {
			return;
		}

		tbody.innerHTML = '';

		data.rounds.forEach(function (round) {
			var dividerRow = document.createElement('tr');
			dividerRow.className = 'matchday-row';
			var dividerCell = document.createElement('td');
			dividerCell.colSpan = 4;
			dividerCell.textContent = round.label;
			dividerRow.appendChild(dividerCell);
			tbody.appendChild(dividerRow);

			round.games.forEach(function (game) {
				var row = document.createElement('tr');

				var dateCell = document.createElement('td');
				dateCell.textContent = formatDate(game.date) + ', ' + game.time;
				row.appendChild(dateCell);

				var homeCell = document.createElement('td');
				homeCell.className = 'col-team';
				homeCell.textContent = game.home;
				row.appendChild(homeCell);

				var awayCell = document.createElement('td');
				awayCell.className = 'col-team';
				awayCell.textContent = game.away;
				row.appendChild(awayCell);

				var resultCell = document.createElement('td');
				resultCell.textContent = game.result || '-:-';
				row.appendChild(resultCell);

				tbody.appendChild(row);
			});
		});
	}

	function computeStandings(data) {
		var tbody = document.getElementById('tabelle-body');
		if (!tbody || !data || !data.rounds) {
			return;
		}

		var stats = {};
		Array.prototype.forEach.call(tbody.querySelectorAll('td.col-team'), function (cell) {
			var name = cell.textContent.trim();
			stats[name] = { name: name, spiele: 0, s: 0, u: 0, n: 0, punkte: 0 };
		});

		data.rounds.forEach(function (round) {
			round.games.forEach(function (game) {
				if (!game.result) {
					return;
				}

				var scores = game.result.split(':');
				var homeGoals = parseInt(scores[0], 10);
				var awayGoals = parseInt(scores[1], 10);
				if (isNaN(homeGoals) || isNaN(awayGoals)) {
					return;
				}

				var home = stats[game.home];
				var away = stats[game.away];
				if (!home || !away) {
					return;
				}

				home.spiele += 1;
				away.spiele += 1;

				if (homeGoals > awayGoals) {
					home.s += 1;
					home.punkte += 3;
					away.n += 1;
				} else if (awayGoals > homeGoals) {
					away.s += 1;
					away.punkte += 3;
					home.n += 1;
				} else {
					home.u += 1;
					away.u += 1;
					home.punkte += 1;
					away.punkte += 1;
				}
			});
		});

		var ranked = Object.keys(stats).map(function (name) {
			return stats[name];
		}).sort(function (a, b) {
			if (b.punkte !== a.punkte) {
				return b.punkte - a.punkte;
			}
			return a.name.localeCompare(b.name);
		});

		tbody.innerHTML = '';
		ranked.forEach(function (team, index) {
			var row = document.createElement('tr');
			if (index === 0) {
				row.className = 'rank-1';
			}

			[index + 1, team.name, team.spiele, team.s, team.u, team.n, team.punkte].forEach(function (value, colIndex) {
				var cell = document.createElement('td');
				if (colIndex === 0) {
					cell.className = 'col-pos';
				} else if (colIndex === 1) {
					cell.className = 'col-team';
				}
				cell.textContent = value;
				row.appendChild(cell);
			});

			tbody.appendChild(row);
		});
	}

	function computeScorers(data) {
		var tbody = document.getElementById('torschuetzen-body');
		if (!tbody || !data || !data.rounds) {
			return;
		}

		var stats = {};
		data.rounds.forEach(function (round) {
			round.games.forEach(function (game) {
				if (!game.scorers) {
					return;
				}
				game.scorers.forEach(function (scorer) {
					var name = scorer[0];
					var team = scorer[1];
					if (!name) {
						return;
					}
					if (!stats[name]) {
						stats[name] = { name: name, team: team, tore: 0 };
					}
					stats[name].tore += 1;
				});
			});
		});

		var scorers = Object.keys(stats).map(function (name) {
			return stats[name];
		}).sort(function (a, b) {
			if (b.tore !== a.tore) {
				return b.tore - a.tore;
			}
			return a.name.localeCompare(b.name);
		});

		tbody.innerHTML = '';

		if (!scorers.length) {
			var emptyRow = document.createElement('tr');
			var emptyCell = document.createElement('td');
			emptyCell.colSpan = 3;
			emptyCell.className = 'empty-state';
			emptyCell.textContent = 'Noch keine Tore erzielt.';
			emptyRow.appendChild(emptyCell);
			tbody.appendChild(emptyRow);
			return;
		}

		scorers.forEach(function (scorer) {
			var row = document.createElement('tr');

			[scorer.name, scorer.team || '-', scorer.tore].forEach(function (value, colIndex) {
				var cell = document.createElement('td');
				if (colIndex < 2) {
					cell.className = 'col-team';
				}
				cell.textContent = value;
				row.appendChild(cell);
			});

			tbody.appendChild(row);
		});
	}

	function loadGames() {
		fetch('data/games2.json')
			.then(function (response) {
				if (!response.ok) {
					throw new Error('Failed to load games');
				}
				return response.json();
			})
			.then(function (data) {
				renderGames(data);
				computeStandings(data);
				computeScorers(data);
			})
			.catch(function () {
				// Keep the existing static empty states.
			});
	}

	buttons.forEach(function (btn) {
		btn.addEventListener('click', function () {
			var target = btn.getAttribute('data-tab');

			buttons.forEach(function (b) {
				b.classList.toggle('active', b === btn);
				b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
			});

			panels.forEach(function (panel) {
				panel.hidden = panel.id !== 'tab-' + target;
			});

			if (titles[target]) {
				document.title = titles[target];
			}
		});
	});

	if (buttons.length) {
		buttons[0].classList.add('active');
	}

	loadGames();
})();

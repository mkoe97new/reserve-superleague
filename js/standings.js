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

	function loadGames() {
		fetch('data/games.json')
			.then(function (response) {
				if (!response.ok) {
					throw new Error('Failed to load games');
				}
				return response.json();
			})
			.then(renderGames)
			.catch(function () {
				// Keep the existing "Spielplan steht noch nicht fest" empty state.
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

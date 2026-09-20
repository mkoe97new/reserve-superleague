(function () {
	var buttons = document.querySelectorAll('.tab-btn');
	var panels = document.querySelectorAll('.tab-panel');
	var titles = {
		tabelle: 'Reserve-Superleague - Tabelle',
		spiele: 'Reserve-Superleague - Spiele',
		torschuetzen: 'Reserve-Superleague - Torschützen'
	};

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
})();

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('themeToggle');
    const root = document.documentElement;

    function applyTheme(theme) {
        if (theme === 'dark') {
            root.classList.add('dark-theme');
            if (toggle) toggle.textContent = '☀️';
        } else {
            root.classList.remove('dark-theme');
            if (toggle) toggle.textContent = '🌙';
        }
    }

    // initialize from localStorage or system
    const saved = localStorage.getItem('twinstock-theme');
    if (saved) {
        applyTheme(saved);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        applyTheme('dark');
    }

    if (toggle) {
        toggle.addEventListener('click', () => {
            const isDark = root.classList.toggle('dark-theme');
            const newTheme = isDark ? 'dark' : 'light';
            localStorage.setItem('twinstock-theme', newTheme);
            applyTheme(newTheme);
        });
    }
});

// Expose a small helper for other scripts
window.twinstockTheme = {
    set: (t) => {
        localStorage.setItem('twinstock-theme', t);
        document.documentElement.classList.toggle('dark-theme', t === 'dark');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const actionBtn = document.getElementById('actionBtn');
    const statusMsg = document.getElementById('statusMsg');

    actionBtn.addEventListener('click', () => {
        statusMsg.textContent = '🎉 Application fonctionnelle et prête !';
        actionBtn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            actionBtn.style.transform = 'scale(1)';
        }, 150);
    });
});

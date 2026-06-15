/**
 * Export Page Controller
 */

document.getElementById('btn-export-ft').addEventListener('click', () => {
    window.open('/api/export/csv', '_blank');
});

document.getElementById('btn-export-anno').addEventListener('click', () => {
    window.open('/api/export/annotations', '_blank');
});

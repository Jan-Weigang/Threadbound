// Allow scrolling to select options
document.querySelectorAll('select').forEach(function(select) {
    if (select.multiple) {
        return;
    }

    if (select.multiple || select.hasAttribute('data-disable-scroll')) {
        return; // Skip select boxes that have the disable attribute or are multiple select
    }

    select.addEventListener('wheel', function(event) {
        event.preventDefault(); // Prevent the page from scrolling when using the mouse wheel on the select box

        const options = select.options;
        const direction = event.deltaY > 0 ? 1 : -1; // Determine scroll direction (down or up)
        const currentIndex = select.selectedIndex;

        let newIndex = currentIndex + direction;

        // Ensure the new index is within bounds
        if (newIndex < 0) {
            newIndex = 0;
        } else if (newIndex >= options.length) {
            newIndex = options.length - 1;
        }

        // Update the selected index
        select.selectedIndex = newIndex;

        // Update the color of the select element after changing the selected option
        if (select.id === 'event_type_id') {
            updateSelectColor(select);
        }

        // If the select is for game categories, update the SVG icon
        if (select.id === 'game_category_id') {
            const iconPreview = document.getElementById('icon-preview');
            updateSelectIcon(select, iconPreview);
        }

        select.dispatchEvent(new Event("change"));
    });
});

// Utility function to format the date as yyyy-mm-dd in local time
function formatDateToYYYYMMDDLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0'); // Add 1 to the month and pad with leading zero if needed
    const day = String(date.getDate()).padStart(2, '0'); // Pad with leading zero if needed
    return `${year}-${month}-${day}`;
}
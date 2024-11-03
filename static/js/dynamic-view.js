
const calendarContainer = document.getElementById('calendar-container');

calendarContainer.addEventListener('htmx:afterSwap', function(event) {
    // const viewType = document.getElementById('viewTypeSelect').value;
    // const date = document.getElementById('dateInput').value;
    const calendar = document.getElementById('calendar');

    set_up_tableHeaders();
    set_up_reservations();
    combine_reservations(calendar);
    initialize_hover();
 
});


document.addEventListener('htmx:afterSwap', function(event) {
    const popup = document.querySelector('.reservation-popup');
    if (popup) {
        shortenLinksInPopup(popup);
    }
})



function calculateSteppedHoverPosition(clientX, calendar) {
    const leftPosition = Math.round((clientX - calendar.getBoundingClientRect().left) / (calendar.clientWidth / 48)) * (calendar.clientWidth / 48);
    const safePosition = Math.max(leftPosition, 0);
    return Math.min(safePosition, calendar.clientWidth * (11 / 12));
}


function set_up_tableHeaders() {
    const tableHeaders = document.querySelectorAll('.table-header');
    const hoverReservations = document.querySelectorAll('.hover-reservation');

    // Add Eventlisteners to table headers
    tableHeaders.forEach((header, index) => {

        const hoverReservation = hoverReservations[index];
        const table_name = header.getAttribute('data-table-info');
        const table_id = header.getAttribute('data-table-id')

        let touchMoveHandler = null;
        let longPressTimer = null;
        let hoverEnabled = false;
        let touchInProgress

        let startX = 0;
        let startY = 0;
        const moveThreshold = 25; // 50 pixel threshold
        const longPressDuration = 500;  // 0.5 seconds

        const swipeDurationThreshold = 300; // Quick swipe duration in ms
        const swipeDistanceThreshold = 50;

        header.addEventListener('touchstart', (e) => {
            touchInProgress = true;  // Set the flag when a touch starts
            e.preventDefault(); 
            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            touchStartTime = Date.now();

            longPressTimer = setTimeout(() => {
                hoverEnabled = true;  // Enable hover functionality after long press
                
                // Hide all other hover reservations
                document.querySelectorAll('.hover-reservation').forEach(hr => {
                    hr.style.display = 'none';
                });
        
                hoverReservation.style.display = 'block';
                activeHoverReservation = hoverReservation;
        
                // Position the hover reservation based on touch location
                const touch = e.touches[0];
                hoverReservation.style.left = `${calculateSteppedHoverPosition(touch.clientX, calendar)}px`;
                hoverReservation.style.width = `${calendar.clientWidth / 12}px`;  // Arbitrary width for visualizing the block
        
                // Add touchmove listener to move the hover reservation along the x-axis
                touchMoveHandler = (moveEvent) => {
                    const moveTouch = moveEvent.touches[0];
                    // hoverReservation.style.left = `${calculateSteppedHoverPosition(moveTouch.clientX, calendar)}px`; // Done: This does not update the info bar yet
                    let timeOffset = calculateSteppedHoverPosition(moveTouch.clientX, calendar)
                    hoverReservation.style.left = `${timeOffset}px`;
                    if (is_inside_header(header, moveEvent)) {
                        header.setAttribute('data-hover-info', `${table_name} - Uhrzeit: ${get_hover_event_time(timeOffset)}`);
                    } else {
                        header.setAttribute('data-hover-info', `Hier loslassen, um abzubrechen.`);
                    }
                };
                header.addEventListener('touchmove', touchMoveHandler);
            }, longPressDuration);  // Trigger hover after 500ms long press

            // Add touchmove listener to track movement and cancel long press if necessary
            header.addEventListener('touchmove', (moveEvent) => {
                const moveTouch = moveEvent.touches[0];
                const deltaX = Math.abs(moveTouch.clientX - startX);
                const deltaY = Math.abs(moveTouch.clientY - startY);

                // Cancel the long press if the movement exceeds the threshold
                if (deltaX > moveThreshold || deltaY > moveThreshold) {
                    clearTimeout(longPressTimer);  // Cancel the long press timer
                }
            });
        });

        header.addEventListener('touchend', (e) => {
            clearTimeout(longPressTimer);

            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const touchEndTime = Date.now();
            const touchDuration = touchEndTime - touchStartTime;

            const deltaX = endX - startX;
            const deltaY = endY - startY;

            // Check for quick swipe
            if (touchDuration < swipeDurationThreshold && Math.abs(deltaX) > swipeDistanceThreshold && Math.abs(deltaY) < swipeDistanceThreshold) {
                const selectedDate = new Date(dateInput.value);
                if (deltaX > 0) {
                    // Swipe right, go to previous day
                    selectedDate.setDate(selectedDate.getDate() - 1);
                } else {
                    // Swipe left, go to next day
                    selectedDate.setDate(selectedDate.getDate() + 1);
                }

                // Format the new date as yyyy-mm-dd
                const formattedDate = selectedDate.toISOString().split('T')[0];

                // Use URLSearchParams to update the date parameter
                const url = new URL(window.location.href);
                url.searchParams.set('date', formattedDate);
                window.location.href = url.toString();
                return;
            }


            if (hoverEnabled && hoverReservation.style.display === 'block' && is_inside_header(header, e)) {

                const timeOffset = e.changedTouches[0].clientX - calendar.getBoundingClientRect().left;
                const time = get_hover_event_time(timeOffset)
                const selectedDate = dateInput.value; 
                window.location.href = `/events/create?table_id=${table_id}&time=${encodeURIComponent(time)}&date=${selectedDate}`;

            }

            // Remove the touchmove listener when the touch ends
            if (touchMoveHandler) {
                header.removeEventListener('touchmove', touchMoveHandler);
            }
            hoverEnabled = false;
            setTimeout(() => {
                touchInProgress = false;  // Clear the flag after a short delay
            }, 300); 
        });


        // Add click event for table booking
        header.addEventListener('click', (e) => {
            if (touchInProgress) {
                e.preventDefault();  // Prevent the click event if it follows a touch
            }
            const timeOffset = e.clientX - calendar.getBoundingClientRect().left;
            const time = get_hover_event_time(timeOffset)
            const selectedDate = dateInput.value; 
            window.location.href = `/events/create?table_id=${table_id}&time=${encodeURIComponent(time)}&date=${selectedDate}`;
        });

        // Add hover effect to show a faded reservation block
        header.addEventListener('mousemove', (e) => {
            hoverReservation.style.display = 'block';
            // hoverReservation.style.left = `${e.clientX - calendar.getBoundingClientRect().left}px`;
            let timeOffset = calculateSteppedHoverPosition(e.clientX, calendar)
            hoverReservation.style.left = `${timeOffset}px`;
            header.setAttribute('data-hover-info', `${table_name} - Uhrzeit: ${get_hover_event_time(timeOffset)}`);
            hoverReservation.style.width = `${calendar.clientWidth / 12}px` // Arbitrary width for visualizing the block
        });
        header.addEventListener('mouseleave', () => {
            hoverReservation.style.display = 'none';
        });


    });
}


function set_up_reservations() {
    const reservations = document.querySelectorAll('.reservation');

    reservations.forEach(reservationBlock => {

        const start = new Date(reservationBlock.getAttribute('data-reservation-start'));
        const end = new Date(reservationBlock.getAttribute('data-reservation-end'));
        const name = reservationBlock.querySelector('.reservation-info-name').textContent;

        const startHour = start.getHours();
        const startMinutes = start.getMinutes();
        const endHour = end.getHours();
        const endMinutes = end.getMinutes();

        // Only show reservations starting after 12:00 PM (noon)
        if (endHour < 12 || startHour > 24) {
            return;
        }

        let durationString = get_duration_string(start, end)
        reservationBlock.setAttribute('data-hover-info', `${name} - ${durationString}`)

        // Adjust the start and duration for the 12:00-24:00 time window
        let adjustedStartHour = startHour - 12;
        let adjustedEndHour = Math.min(12, (endHour > 24 ? 24 : endHour) - 12);

        let has_openStart = false
        if (adjustedStartHour < 0) {
            adjustedStartHour = 0;
            has_openStart = true;
        }

        // Calculate start position and height based on both hours and minutes
        const startOffset = adjustedStartHour + (startMinutes / 60);
        const endOffset = adjustedEndHour + (endMinutes / 60);
        const duration = endOffset - startOffset;

        // Position the block within the day timeline
        reservationBlock.style.left = `${(startOffset / 12) * 100}%`;
        reservationBlock.style.width = `${(duration / 12) * 100}%`;
        let reservation_time_string = `${startHour}:${startMinutes.toString().padStart(2, '0')} bis ${endHour}:${endMinutes.toString().padStart(2, '0')}`

        // add time info
        const timeElement = reservationBlock.querySelector('.reservation-info-time');
        timeElement.textContent = reservation_time_string;
        
        if (has_openStart) { // Make borders look open to left side for earlier beginning reservations.
            reservationBlock.style.borderRadius = "0px 10px 10px 0px"; 
            reservationBlock.style.borderLeft = "none";
        }

    });
}


// Function to combine reservations on consequtive tables with same event id
function combine_reservations(calendar) {
    const reservationBlocks = Array.from(calendar.children).filter(child => child.classList.contains('reservation'));
        
    // Sort by reservation ID and then by table row
    reservationBlocks.sort((a, b) => {
        const idA = a.getAttribute('data-event-id');
        const idB = b.getAttribute('data-event-id');
        const rowA = parseInt(a.getAttribute('data-table-id'), 10);
        const rowB = parseInt(b.getAttribute('data-table-id'), 10);

        if (idA !== idB) return idA.localeCompare(idB);
        return rowA - rowB;
    });



    let previousBlock = null;

    reservationBlocks.forEach((block, index) => {
        const currentId = block.getAttribute('data-event-id');
        const currentRow = parseInt(block.getAttribute('data-table-id'), 10);

        if (previousBlock) {
            const previousId = previousBlock.getAttribute('data-event-id');
            const previousEndRow = parseInt(previousBlock.style.gridRowEnd, 10);

            // Check if current block is part of the same reservation on consecutive rows
            if (currentId === previousId && currentRow === previousEndRow) {
                // Extend the previous block's grid-row-end to cover this block's row
                previousBlock.style.gridRowEnd = currentRow + 1;

                // Remove the current block as it's merged with the previous block
                block.remove();
                return; // Skip the rest of this iteration
            }
        }

        // Set grid-row-start and grid-row-end for each block initially
        block.style.gridRowStart = currentRow;
        block.style.gridRowEnd = currentRow + 1;

        // Update the previous block reference for the next iteration
        previousBlock = block;
    });

}


function get_hover_event_time(timeOffset) {
    const timePercentage = timeOffset / calendar.clientWidth;
    const hours = 12 + timePercentage * 12;
    let roundedHours = Math.floor(hours);
    let minutes = Math.round((hours - roundedHours) * 60);

    // Adjust if minutes equal 60
    if (minutes === 60) {
        minutes = 0;
        roundedHours += 1;
    }

    // Wrap hours if it reaches 24
    if (roundedHours === 24) {
        roundedHours = 0;
    }

    // Format time with padded minutes
    const time = `${roundedHours}:${minutes.toString().padStart(2, '0')}`;
    return time;
}


function shortenLinksInPopup(popup) {
    const popupDivs = popup.querySelectorAll('.popup-value');
    
    // Regex pattern to find URLs (including discord://)
    const urlPattern = /(https?:\/\/|discord:\/\/|www\.)[^\s]+/g;

    popupDivs.forEach(div => {
        div.innerHTML = div.innerHTML.replace(urlPattern, (url) => {
            let displayURL, href, target;

            // Check if it's a discord:// link
            if (url.startsWith("discord://")) {
                // Parse the URL manually since `new URL` won't work with `discord://`
                displayURL = "discord.com/..";
                href = url; // Keep the original `discord://` link
                target = "_self"; // Open in the same tab for discord links
            } else {
                // For standard URLs, use `new URL` to parse
                const urlObject = new URL(url.startsWith("http") ? url : `https://${url}`);
                const domain = urlObject.hostname;
                const displayPath = urlObject.pathname.length > 1 ? '/..' : '';
                displayURL = `${domain}${displayPath}`;
                href = urlObject.href;
                target = "_blank"; // Open in a new tab for regular links
            }

            // Return an anchor with the appropriate display text, href, and target
            return `<a href="${href}" target="${target}" rel="noopener noreferrer">${displayURL}</a>`;
        });
    });
}


function get_duration_string(start, end) {
    // Calculate the difference in milliseconds
    let durationMs = end - start;

    // Calculate hours and minutes separately
    let event_hours = Math.floor(durationMs / (1000 * 60 * 60));
    let event_minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));

    // Format the duration string
    if (event_minutes == 0) {
        return `${event_hours} Std`;
    } else {
        return `${event_hours} Std ${event_minutes} Min`;
    }
    
}


function is_inside_header(header, e) {
    // Get the current touch position
    const touch = e.changedTouches[0];
    const touchX = touch.clientX;
    const touchY = touch.clientY;

    // Get header bounds
    const headerRect = header.getBoundingClientRect();

    // Check if touch ended inside the header boundaries
    const isInsideHeader = (
        touchX >= headerRect.left &&
        touchX <= headerRect.right &&
        touchY >= headerRect.top &&
        touchY <= headerRect.bottom
    );

    return isInsideHeader;
}

// Month view on dateInput
// document.addEventListener('DOMContentLoaded', function() {
//     document.querySelector('.calendar-container').addEventListener('click', (e) => {
        
//         const container = e.currentTarget;
//         const dateInput = document.getElementById('dateInput');
//         const currentDate = dateInput.value;

//         // Determine direction based on clicked element
//         if (e.target === container.querySelector('::before')) {
//             // Previous day
//             currentDate.setDate(currentDate.getDate() - 1);
//             // Format date to yyyy-mm-dd
//             const formattedDate = currentDate.toISOString().split('T')[0];
            
//             // Redirect to the new date
//             window.location.href = `/day/${formattedDate}`;
//         } else if (e.target === container.querySelector('::after')) {
//             // Format date to yyyy-mm-dd
//             const formattedDate = currentDate.toISOString().split('T')[0];
            
//             // Redirect to the new date
//             window.location.href = `/day/${formattedDate}`;
//         }

        
//     });
// });

// Prev and Next Logix KEEP THIS
// document.addEventListener('DOMContentLoaded', () => {
//     const dateInput = document.getElementById('dateInput');
//     const url = dateInput.getAttribute('data-url-day');
//     const prevDay = document.querySelector('.prev-day');
//     const nextDay = document.querySelector('.next-day');

//     prevDay.addEventListener('click', () => {
//         // Get current date from dateInput
//         const currentDate = new Date(dateInput.value);
//         currentDate.setDate(currentDate.getDate() - 1); // Move to previous day

//         // Format date as yyyy-mm-dd
//         const formattedDate = currentDate.toISOString().split('T')[0];
//         window.location.href = `${url}?date=${formattedDate}`; // Redirect to previous day
//     });

//     nextDay.addEventListener('click', () => {
//         // Get current date from dateInput
//         const currentDate = new Date(dateInput.value);
//         currentDate.setDate(currentDate.getDate() + 1); // Move to next day

//         // Format date as yyyy-mm-dd
//         const formattedDate = currentDate.toISOString().split('T')[0];
//         window.location.href = `${url}?date=${formattedDate}`; // Redirect to next day
//     });
// });
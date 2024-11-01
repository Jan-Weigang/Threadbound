const viewType = document.querySelector('meta[name="view-type"]').content;
const date = document.querySelector('meta[name="date"]').content;
const reservationsUrl = `/api/reservations/${viewType}?date=${date}`;


let tables = [];
let reservations = [];
let eventTypes = [];

document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('viewTypeSelect').value = viewType;
    document.getElementById('dateInput').value = date;
    console.log("MY DATE IS   " + date)


    Promise.all([
        fetch('/api/tables').then(response => response.json()),
        fetch(reservationsUrl).then(response => response.json()),
        fetch('/api/event-types').then(response => response.json())
    ]).then(([tableData, reservationData, eventTypeData]) => {
        // console.log("Tables Data:", tableData);
        // console.log("Reservations Data:", reservationData);
        // console.log("Event Types Data:", eventTypeData);

        tables = tableData.tables;
        reservations = reservationData.reservations;
        eventTypes = eventTypeData.event_types;
        const calendar = document.getElementById('calendar');

        // Create a lookup for event type colors
        const eventTypeColorMap = {};
        eventTypes.forEach(eventType => {
            eventTypeColorMap[eventType.id] = eventType.color;
        });

        // Set the number of columns based on the number of tables
        const rowSizes = tables.map(table => `${table.capacity}fr`).join(' ');
        calendar.style.gridTemplateRows = rowSizes;

        // Function to calculate the stepped hover left position
        function calculateSteppedHoverPosition(clientX, calendar) {
            const leftPosition = Math.round((clientX - calendar.getBoundingClientRect().left) / (calendar.clientWidth / 48)) * (calendar.clientWidth / 48);
            const safePosition = Math.max(leftPosition, 0);
            return Math.min(safePosition, calendar.clientWidth * (11 / 12));
        }

        // Add table headers
        tables.forEach((table, index) => {
            // console.log("Adding Table Header:", table);
            const header = document.createElement('div');
            header.className = 'table-header';
            header.style.gridRow = `${index + 1} / ${index + 2}`;
            // Set background color based on table type
            if (table.type === "RPG") {
                header.style.backgroundColor = 'var(--accent-color-light)';
            }
            header.setAttribute('data-table-info', `${table.name}`);
            header.setAttribute('data-hover-info', `Tisch: ${table.name} - Kapazität: ${table.capacity}`); // Default hover info
            calendar.appendChild(header);

            // Create hover reservation block for each table header
            const hoverReservation = document.createElement('div');
            hoverReservation.className = 'hover-reservation';
            hoverReservation.style.gridRow = `${index + 1} / ${index + 2}`;
            calendar.appendChild(hoverReservation);


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
                            header.setAttribute('data-hover-info', `${table.name} - Uhrzeit: ${get_hover_event_time(timeOffset)}`);
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
                    const tableId = table.id;
                    const selectedDate = dateInput.value; 
                    window.location.href = `/events/create?table_id=${tableId}&time=${encodeURIComponent(time)}&date=${selectedDate}`;

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
                const tableId = table.id;
                const selectedDate = dateInput.value; 
                window.location.href = `/events/create?table_id=${tableId}&time=${encodeURIComponent(time)}&date=${selectedDate}`;
            });

            // Add hover effect to show a faded reservation block
            header.addEventListener('mousemove', (e) => {
                hoverReservation.style.display = 'block';
                // hoverReservation.style.left = `${e.clientX - calendar.getBoundingClientRect().left}px`;
                let timeOffset = calculateSteppedHoverPosition(e.clientX, calendar)
                hoverReservation.style.left = `${timeOffset}px`;
                header.setAttribute('data-hover-info', `${table.name} - Uhrzeit: ${get_hover_event_time(timeOffset)}`);
                hoverReservation.style.width = `${calendar.clientWidth / 12}px` // Arbitrary width for visualizing the block
            });
            header.addEventListener('mouseleave', () => {
                hoverReservation.style.display = 'none';
            });


        });

        // Add reservations as blocks (for hours between 12:00 to 24:00)
        reservations.forEach(reservation => {
            // console.log("Processing Reservation:", reservation);
            const start = new Date(reservation.start_time);
            const end = new Date(reservation.end_time);

            const startHour = start.getHours();
            const startMinutes = start.getMinutes();
            const endHour = end.getHours();
            const endMinutes = end.getMinutes();

            // Only show reservations starting after 12:00 PM (noon)
            if (endHour < 12 || startHour > 24) {
                // console.log(`Reservation ${reservation.id} is outside displayable hours.`);
                return;
            }

            const reservationBlock = document.createElement('div');
            reservationBlock.className = 'reservation';

            let durationString = get_duration_string(start, end)
            reservationBlock.setAttribute('data-hover-info', `${reservation.name} - ${durationString}`)

            // Set the color based on the event type color from the lookup map
            const eventColor = eventTypeColorMap[reservation.event_type_id] || '#3788d8'; // Fallback color if none is provided
            reservationBlock.style.backgroundColor = eventColor;

            // Adjust the start and duration for the 12:00-24:00 time window
            let adjustedStartHour = startHour - 12;
            let adjustedEndHour = Math.min(12, (endHour > 24 ? 24 : endHour) - 12);

            let openStart = false

            if (adjustedStartHour < 0) {
                adjustedStartHour = 0;
                openStart = true;
            }

            // Calculate start position and height based on both hours and minutes
            const startOffset = adjustedStartHour + (startMinutes / 60);
            const endOffset = adjustedEndHour + (endMinutes / 60);
            const duration = endOffset - startOffset;

            // Set the column for the reservation block explicitly
            const rowIndex = tables.findIndex(table => table.id === reservation.table_id);
            if (rowIndex === -1) {
                console.error(`Table ID ${reservation.table_id} not found.`);
                return;
            }
            reservationBlock.style.gridRowStart = rowIndex + 1;
            reservationBlock.style.gridRowEnd = rowIndex + 2;

            // Position the block within the day timeline
            reservationBlock.style.left = `${(startOffset / 12) * 100}%`;
            reservationBlock.style.width = `${(duration / 12) * 100}%`;
            // let reservation_name = reservation.name.length > 5 ? reservation.name.substring(0, 10) + '..' : reservation.name;
            let reservation_name = reservation.name;
            let reservation_time_string = `${startHour}:${startMinutes.toString().padStart(2, '0')} bis ${endHour}:${endMinutes.toString().padStart(2, '0')}`
            
            const reservationWrap = document.createElement('div');
            reservationWrap.classList.add("reservation-wrapper");

            const nameElement = document.createElement('b');
            nameElement.textContent = reservation_name;
            nameElement.classList.add("reservation-info-name")
            reservationWrap.appendChild(nameElement);

            const timeElement = document.createElement('i');
            timeElement.textContent = reservation_time_string;
            timeElement.classList.add("reservation-info-time");
            reservationWrap.appendChild(timeElement);

            const attendeeElement = document.createElement('span');
            attendeeElement.innerHTML = `${reservation.attendee_count} Personen`;
            attendeeElement.classList.add("reservation-info-attendees")
            reservationWrap.appendChild(attendeeElement);

            const descElement = document.createElement('span');
            descElement.textContent = reservation.publicity;
            descElement.classList.add("reservation-info-publicity")
            reservationWrap.appendChild(descElement);
            
            // reservationBlock.innerHTML = `<b>${reservation_name}</b> <i style="color: grey;">${reservation_time_string}</i>`;
            if (openStart) { // Make borders look open to left side for earlier beginning reservations.
                reservationBlock.style.borderRadius = "0px 10px 10px 0px"; 
                reservationBlock.style.borderLeft = "none";
            }


            // Add game category icon in the bottom right
            if (reservation.game_category_icon) {
                const iconImg = document.createElement('img');
                iconImg.src = `data:image/svg+xml;base64,${reservation.game_category_icon}`;
                iconImg.style.width = '20px';
                iconImg.style.height = '20px';
                iconImg.classList.add("reservation-info-icon");
                reservationWrap.appendChild(iconImg);
            }

            reservationBlock.appendChild(reservationWrap)
            // Add data attributes for reservation ID and table row
            reservationBlock.setAttribute('data-event-id', reservation.event_id);
            reservationBlock.setAttribute('data-table-row', reservation.table_id);

            reservationBlock.addEventListener('click', function() {
                openReservationPopup(reservation);
            });

            // console.log("Adding Reservation Block:", reservationBlock);
            calendar.appendChild(reservationBlock);

        });

        combine_reservations(calendar);



    }).catch(error => {
        console.error("Error fetching data:", error);
    });
});

// function openOverlay(url) {
//     const overlay = document.getElementById('overlay');
//     const iframe = document.getElementById('overlay-iframe');
//     iframe.src = url;
//     overlay.style.display = 'flex';
// }

// function closeOverlay() {
//     const overlay = document.getElementById('overlay');
//     overlay.style.display = 'none';
//     document.getElementById('overlay-iframe').src = "";
//     window.location.reload();
// }

// Function to combine reservations on consequtive tables with same event id
function combine_reservations(calendar) {
    const reservationBlocks = Array.from(calendar.children).filter(child => child.classList.contains('reservation'));
        
    // Sort by reservation ID and then by table row
    reservationBlocks.sort((a, b) => {
        const idA = a.getAttribute('data-event-id');
        const idB = b.getAttribute('data-event-id');
        const rowA = parseInt(a.getAttribute('data-table-row'), 10);
        const rowB = parseInt(b.getAttribute('data-table-row'), 10);

        if (idA !== idB) return idA.localeCompare(idB);
        return rowA - rowB;
    });



    let previousBlock = null;

    reservationBlocks.forEach((block, index) => {
        const currentId = block.getAttribute('data-event-id');
        const currentRow = parseInt(block.getAttribute('data-table-row'), 10);

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

// Function to create a stylized popup
function openReservationPopup(reservation) {
    const table = tables.find(tbl => tbl.id == reservation.table_id);
    const event_type = eventTypes.find(typ => typ.id == reservation.event_type_id);
    const relatedTables = reservations.filter(res => res.event_id == reservation.event_id).map(res => tables.find(tbl => tbl.id == res.table_id)).filter(table => table);

    // Create the popup container
    const popup = document.createElement('div');
    popup.className = 'reservation-popup';

    // Create the content wrapper
    const popupContent = document.createElement('div');
    popupContent.className = 'popup-content';

    console.log(reservation);
    console.log(table);

    let start_time = new Date(reservation.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
    let end_time = new Date(reservation.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })

    // Add related tables information
    const relatedTablesInfo = relatedTables.map(table => table.name).join(', ');

    // Add reservation information
    const fields = [
        { label: event_type.name, value: reservation.name, heading: true },
        { label: reservation.game_category, value: reservation.publicity },
        { label: 'Uhrzeit:', value:  start_time + " Uhr bis " + end_time + " Uhr" },
        { label: 'Tische:', value: relatedTablesInfo },
        ...(reservation.attendee_count != null ? [{ label: 'Teilnehmende:', value: reservation.attendee_count + " Personen" }] : []),
        { label: 'Discord:', value: 'App: discord://' + reservation.discord_link + ' - Web: https://' + reservation.discord_link },
        { label: 'Beschreibung:', value: reservation.description },
        
    ];

    fields.forEach(field => {

        const label = document.createElement('div');
        label.textContent = field.label;

        const value = document.createElement('div');
        value.textContent = field.value;

        if (field.heading) {
            label.className = 'popup-label';
            value.className = 'popup-heading';
        }
        else {
            label.className = 'popup-label';
            value.className = 'popup-value';
        }

        
        

        popupContent.appendChild(label);
        popupContent.appendChild(value);
        
    });
    
    // Append the content to the popup
    popup.appendChild(popupContent);

    const footer = document.createElement('div');
    footer.className ='popup-footer';

    // Add Creator Info
    const creator_info = document.createElement('div');
    creator_info.className = 'creator-info';

    const author = document.createElement('span');
    author.innerHTML = reservation.user_name;
    creator_info.appendChild(author);

    const lastTouched = document.createElement('span');
    if (reservation.time_updated) {
        lastTouched.innerHTML = "Editiert am " + reservation.time_updated;
    }
    else {
        lastTouched.innerHTML = "Erstellt am " + reservation.time_created;
    }
    creator_info.appendChild(lastTouched);
    
    
    // creator_info.innerHTML = "Erstellt von <b>" + reservation.user_name + "</b> am " + reservation.time_created;
    


    footer.appendChild(creator_info);
    
    const footer_buttons = document.createElement('div');
    footer_buttons.className = 'popup-footer-buttons';
    footer.appendChild(footer_buttons);


    // Add an edit button
    const editButton = document.createElement('button');
    editButton.className = 'edit-popup';
    editButton.textContent = 'Editieren';
    editButton.addEventListener('click', () => {
        // Assuming you have access to the event ID
        const eventId = reservation.event_id; 

        // Redirect to the edit page for the event
        window.location.href = `/events/edit/${eventId}`;
    });
    footer_buttons.appendChild(editButton);

    // Add a close button
    const closeButton = document.createElement('button');
    closeButton.className = 'close-popup';
    closeButton.textContent = 'Schließen';
    closeButton.addEventListener('click', () => {
        document.body.removeChild(popup);
    });
    footer_buttons.appendChild(closeButton);

    
    

    
    footer.appendChild(footer_buttons)
    popup.appendChild(footer);

    shortenLinksInPopup(popup);

    // Append the popup to the body
    document.body.appendChild(popup);

    // Add an event listener to close the popup when clicking outside of it
    function closeOnOutsideClick(event) {
        if (!popup.contains(event.target)) {
            document.body.removeChild(popup);
            document.removeEventListener('click', closeOnOutsideClick);
        }
    }
    setTimeout(() => document.addEventListener('click', closeOnOutsideClick), 0);
}



const viewTypeSelect = document.getElementById('viewTypeSelect');
const dateInput = document.getElementById('dateInput');

// Add event listeners to both the viewTypeSelect and dateInput
viewTypeSelect.addEventListener('change', updateCalendarView);
// dateInput.addEventListener('change', updateCalendarView); // TODO Month View instead of selecting cate here
dateInput.addEventListener('click', function(e) {
    e.preventDefault();
    const url = this.getAttribute('data-url-month');
    window.location.href = url;
})

// Function to handle the redirection based on view type and date
function updateCalendarView() {
    const viewType = viewTypeSelect.value;  // Get the selected view type
    const selectedDate = dateInput.value;   // Get the selected date
    window.location.href = `/calendar/day/${viewType}?date=${selectedDate}`;  // Redirect to the new URL
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

// function get_hover_event_time(timeOffset) {
//     const timePercentage = timeOffset / calendar.clientWidth;
//     const hours = 12 + timePercentage * 12;
//     const roundedHours = Math.floor(hours);
//     const minutes = Math.round((hours - roundedHours) * 60);
//     const time = `${roundedHours}:${minutes.toString().padStart(2, '0')}`;
//     return time
// }

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

// // Shorten links in a specific popup element before appending
// function shortenLinksInPopup(popup) {
//     // Select all elements in the popup with the class 'popup-value'
//     const popupDivs = popup.querySelectorAll('.popup-value');
    
//     // Regex pattern to find URLs
//     //const urlPattern = /(https?:\/\/|www\.)[^\s]+/g;
//     const urlPattern = /(https?:\/\/|discord:\/\/|www\.)[^\s]+/g;

//     popupDivs.forEach(div => {
//         // Replace URLs in the div's text content with anchor tags
//         div.innerHTML = div.innerHTML.replace(urlPattern, (url) => {
//             // Parse the URL to handle formatting consistently
//             const urlObject = new URL(url.startsWith("http") ? url : `https://${url}`);
            
//             // Get the domain (e.g., "meineSeite.de")
//             const domain = urlObject.hostname;
            
//             // Determine if there is a path beyond the root
//             const displayPath = urlObject.pathname.length > 1 ? '/..' : '';

//             // Construct the shortened display URL
//             const shortenedDisplayURL = `${domain}${displayPath}`;

//             // Return an anchor with the shortened display text
//             return `<a href="${urlObject.href}" target="_blank" rel="noopener noreferrer">${shortenedDisplayURL}</a>`;
//         });
//     });
// }

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


document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('dateInput');
    const url = dateInput.getAttribute('data-url-day');
    const prevDay = document.querySelector('.prev-day');
    const nextDay = document.querySelector('.next-day');

    prevDay.addEventListener('click', () => {
        // Get current date from dateInput
        const currentDate = new Date(dateInput.value);
        currentDate.setDate(currentDate.getDate() - 1); // Move to previous day

        // Format date as yyyy-mm-dd
        const formattedDate = currentDate.toISOString().split('T')[0];
        window.location.href = `${url}?date=${formattedDate}`; // Redirect to previous day
    });

    nextDay.addEventListener('click', () => {
        // Get current date from dateInput
        const currentDate = new Date(dateInput.value);
        currentDate.setDate(currentDate.getDate() + 1); // Move to next day

        // Format date as yyyy-mm-dd
        const formattedDate = currentDate.toISOString().split('T')[0];
        window.location.href = `${url}?date=${formattedDate}`; // Redirect to next day
    });
});
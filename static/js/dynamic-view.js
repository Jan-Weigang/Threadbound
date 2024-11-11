let occupancyByDay = {};

// Page Setup
document.addEventListener('DOMContentLoaded', () => {

    const dateInput = document.getElementById('dateInput');

    // enable Date Changing via buttons
    const dateButtons = document.querySelectorAll('.date-changer');
    dateButtons.forEach(button => {
        button.addEventListener('click', () => {
            const wrapper = document.getElementById('layoutWrapper');
            layout = wrapper.getAttribute('data-layout');
            const amount = parseInt(button.getAttribute('data-amount'), 10);

            if (layout == 'month') {
                const mode = button.getAttribute('data-mode');
                newDate = get_new_date_changed_month(amount, mode)
                change_dateInput_to(newDate);
            } else {
                change_dateInput_by(amount);
            }
        });
    });

    // initialize Layout Buttons
    set_layout_buttons('mixed');

    // enable layout Change via buttons
    const layoutButtons = document.querySelectorAll('.layout-picker-button');
    layoutButtons.forEach(button => {
        button.addEventListener('click', () => {
            attribute_string = button.getAttribute('data-layout');
            set_layout_buttons(attribute_string);
        });
    });

    // Initialize Month Shortcut
    const datePickerButton = document.getElementById('datePickerButton');

    datePickerButton.addEventListener('click', function () {
        set_layout_buttons('month');
    });

    
    // Fill Calendar on load.
    htmx.ajax('GET', `/calendar/fetch/month?date=${encodeURIComponent(dateInput.value)}`, { target: '#calendar-grid' });
    

    // Catchall EventListener for Date Changes
    let currentMonth = new Date(document.getElementById('dateInput').value).getMonth();
    dateInput.addEventListener('change', function() {

        // Trigger Calendar UI Updates
        const newDate = new Date(dateInput.value);
        const newMonth = newDate.getMonth();
        if (newMonth !== currentMonth) {
            currentMonth = newMonth; // Update the current month to the new month
            htmx.ajax('GET', `/calendar/fetch/month?date=${encodeURIComponent(dateInput.value)}`, { target: '#calendar-grid' });
        } else {
            updateCalendarClasses(newDate);
        }
    });
});



const calendarContainer = document.getElementById('calendar-container');

// Calendar Setup
calendarContainer.addEventListener('htmx:afterSwap', function(event) {
    // const viewType = document.getElementById('viewTypeSelect').value;
    // const date = document.getElementById('dateInput').value;
    const dateInput = document.getElementById('dateInput');
    const currentDate = new Date(dateInput.value);
    const heading = document.getElementById('viewHeading');
    const formattedDate = new Intl.DateTimeFormat('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(currentDate);
    heading.textContent = formattedDate;


    const calendar = document.getElementById('calendar');

    set_up_tableHeaders();
    set_up_reservations();
    combine_reservations(calendar);
    initialize_hover();
 
});

const calendarGrid = document.getElementById('calendar-grid');

calendarGrid.addEventListener('htmx:afterSwap', function(event) {
    renewCalendarGridEventListeners();

    const newDate = new Date(dateInput.value);
    updateCalendarClasses(newDate);
});

document.addEventListener('gridLoaded', function() {
    updateDayElements();
    initialize_hover();
});


// Small Updates after any htmx requests
document.addEventListener('htmx:afterSwap', function(event) {
    const popup = document.querySelector('.reservation-popup');
    if (popup) {
        shortenLinksInPopup(popup);
    }

    const prevDay = document.querySelector('.prev-day');
    const nextDay = document.querySelector('.next-day');

    prevDay.addEventListener('click', () => {
        change_dateInput_by(-1);
    });

    nextDay.addEventListener('click', () => {
        change_dateInput_by(1);
    });
})

function change_dateInput_by(dayAmount) {
    const dateInput = document.getElementById('dateInput');
    const currentDate = new Date(dateInput.value);
        // Use UTC methods to prevent DST issues
        const utcDate = new Date(Date.UTC(
            currentDate.getUTCFullYear(),
            currentDate.getUTCMonth(),
            currentDate.getUTCDate()
        ));
        utcDate.setUTCDate(utcDate.getUTCDate() + dayAmount);
        const formattedDate = utcDate.toISOString().split('T')[0];
        dateInput.value = formattedDate;
        dateInput.dispatchEvent(new Event('change'));
}

function change_dateInput_to(yyyy_mm_dd) {
    const dateInput = document.getElementById('dateInput');
    dateInput.value = yyyy_mm_dd;
    dateInput.dispatchEvent(new Event('change'));
}

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



function updateCalendarClasses(date) {
    const weekStart = new Date(date);
    if (weekStart.getDay() === 0) {
        // If Sunday
        weekStart.setDate(weekStart.getDate() - 6);
    } else {
        weekStart.setDate(weekStart.getDate() - (weekStart.getDay() - 1));
    }
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);

    // Select all day elements inside the calendar grid
    const dayElements = document.querySelectorAll('#calendar-grid .day');

    dayElements.forEach(dayElement => {
        // Get the date attribute and parse it into a Date object
        const divDate = new Date(dayElement.getAttribute('data-date'));

        // Remove any existing classes
        dayElement.classList.remove('active-month', 'other-month', 'active-day', 'not-active-week');

        // Add class for active month or other month
        if (divDate.getMonth() === date.getMonth()) {
            dayElement.classList.add('active-month');
        } else {
            dayElement.classList.add('other-month');
        }

        // Add class for active day (today)
        if (divDate.toDateString() === date.toDateString()) {
            dayElement.classList.add('active-day');
        }

        // Add class for not-active-week if the day is outside the current week
        if (divDate < weekStart || divDate > weekEnd) {
            dayElement.classList.add('not-active-week');
        }

        const localDayString = divDate.toLocaleString('de-DE', { weekday: 'short' })
        dayElement.classList.add(localDayString.toLowerCase());
    });

}

function renewCalendarGridEventListeners() {
    const dayElements = document.querySelectorAll('#calendar-grid .day');
    const dateInput = document.getElementById('dateInput');

    // Click event for grid
    dayElements.forEach(dayElement => {
        dayElement.addEventListener('click', function() {
            const date_str = dayElement.getAttribute('data-date');
            dateInput.value = date_str;
            dateInput.dispatchEvent(new Event('change'));
            const wrapper = document.getElementById('layoutWrapper');
            const layout = wrapper.getAttribute('data-layout')
            const is_grid = 'month';
            if (layout == is_grid) {
                wrapper.setAttribute('data-layout', 'mixed');
                set_layout_buttons('mixed');
            }
        });
    });
}



function set_layout_buttons(attribute_string) {
    const wrapper = document.getElementById('layoutWrapper');
    wrapper.setAttribute('data-layout', attribute_string);

    const layoutButtons = document.querySelectorAll('.layout-picker-button');
    layoutButtons.forEach(button => {
        button.classList.remove('set');
        buttonAttribute = button.getAttribute('data-layout');
        if (buttonAttribute == attribute_string) {
            button.classList.add('set');
        }
    });
}

function get_new_date_changed_month(amount, mode) {
    if (mode == 'weekday') {
        return get_new_date_for_weekday(amount);
    } else {
        return get_new_date_for_day(amount);
    }
}

function get_new_date_for_day(amount) {
    const dateInput = document.getElementById('dateInput');
    const currentValue = dateInput.value;
    let [year, month, day] = currentValue.split('-');
    month = parseInt(month, 10);

    // change based on button
    if (amount < 0) {
        month -= 1;
    } else {
        month += 1;
    }
    // check month overflow
    if (month > 12) {
        month = 1;
        year = parseInt(year, 10) + 1; 
    } else if (month < 1) {
        month = 12;
        year = parseInt(year, 10) - 1; 
    }
    month = month.toString().padStart(2, '0');
    const newDateValue = `${year}-${month}-${day}`;
    return newDateValue
}

function get_new_date_for_weekday(amount) {
    const dateInput = document.getElementById('dateInput');
    const currentValue = dateInput.value;
    let [year, month, day] = currentValue.split('-');
    month = parseInt(month, 10);
    day = parseInt(day, 10);

    const currentDate = new Date(year, month - 1, day);
    const currentWeekday = currentDate.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday


    // Calculate which nth occurrence of the current weekday it is in the current month
    let count = 0;
    for (let d = 1; d <= day; d++) {
        const tempDate = new Date(year, month - 1, d);
        if (tempDate.getDay() === currentWeekday) {
            count++;
        }
    }

    // Change the month by the specified amount
    if (amount < 0) {
        month -= 1;
    } else {
        month += 1;
    }

    // Handle month overflow
    if (month > 12) {
        month = 1;
        year = parseInt(year, 10) + 1;
    } else if (month < 1) {
        month = 12;
        year = parseInt(year, 10) - 1;
    }

    // Find the nth occurrence of the weekday in the new month
    let newDay = null;
    let occurrence = 0;
    for (let d = 1; d <= 31; d++) {
        const tempDate = new Date(year, month - 1, d);
        if (tempDate.getMonth() !== month - 1) break; // Stop if we move into the next month
        if (tempDate.getDay() === currentWeekday) {
            occurrence++;
            if (occurrence === count) {
                newDay = d;
                break;
            }
        }
    }

    // If not found, fallback to the last valid weekday (4th occurrence max)
    if (newDay === null) {
        newDay = occurrence > 0 ? occurrence * 7 - (7 - currentWeekday) : day;
    }

    month = month.toString().padStart(2, '0');
    newDay = newDay.toString().padStart(2, '0');
    return `${year}-${month}-${newDay}`;
}

function updateDayElements() {
    const daysContainer = document.getElementById('calendar-grid');
    const dayElements = daysContainer.querySelectorAll('.day');
    
    for (let i = 0; i < dayElements.length; i++) {
        const dayElement = dayElements[i];
        const eventDateKey = dayElement.getAttribute('data-date');

        // Create the heat-bar-graph for each hour
        const heatBar = dayElement.querySelector('.heat-bar');
        const occupancyThisDay = occupancyByDay[eventDateKey] || Array(24).fill(0); // Fallback to an empty array with 13 zeroes

        // Calculate the gradient stops based on booked capacity vs total capacity with abrupt transitions
        const gradientStops = occupancyThisDay.map((percentageBooked, index) => {
            const start = (index / 24) * 100;
            const end = ((index + .3) / 24) * 100;
            const color = getHeatColor(percentageBooked);

            return `${color} ${start}%, ${color} ${end}%`; // Set abrupt color change between start and end
        }).join(',');
        heatBar.style.background = `linear-gradient(to right, ${gradientStops})`;

        // Create a set to track unique events for this day
        const eventIdsForDay = new Set();
        const reservations = Array.from(dayElement.getElementsByClassName('event'));

        // Remove double events
        reservations.forEach(reservation => {
            const eventId = reservation.getAttribute('data-event-id');
            if (eventIdsForDay.has(eventId)) {
                reservation.remove(); // Remove the reservation element from the DOM if it's a duplicate
            } else {
                eventIdsForDay.add(eventId);
            }
        });

        hoverInfo = get_hover_info_for_dayElement(occupancyThisDay, eventIdsForDay.size);
        dayElement.setAttribute('data-hover-info', hoverInfo);
    }
}

// Helper function to get a color based on percentage booked using CSS lab() color space
function getHeatColor(percentage) {
    // Clamp the percentage between 0 and 1 to avoid out-of-bounds values
    percentage = Math.max(0, Math.min(percentage, 1));

    // Interpolate between lab(100% 60 -100) for green and lab(55% 60 40) for red
    const labStart = [100, 3, -9];  // lab(100% 60 -100) -> Green
    const labEnd = [0, 128, -85];       // lab(55% 60 40) -> Red

    const lastFivePercent = Math.max(Math.min(1, percentage * -20 + 19),0)

    // Interpolate each lab component
    const L = labStart[0] + (labEnd[0] - labStart[0]) * percentage;
    const a = labStart[1] + (labEnd[1] - labStart[1]) * Math.min(Math.max(0, percentage * 2 - .7),1) * lastFivePercent;
    const b = labStart[2] + (labEnd[2] - labStart[2]) * Math.min(1, percentage * 2) * lastFivePercent;

    // Return the color in CSS lab() format
    return `lab(${L}% ${a} ${b})`;
}

function get_hover_info_for_dayElement(occupancyThisDay, event_count) {
    
    const avgOccupancy = occupancyThisDay.reduce((a, b) => a + b, 0) / occupancyThisDay.length;

    // Determine peak hours based on 50% capacity
    let peakStart = null, peakEnd = null;
    const peakHour = occupancyThisDay.indexOf(Math.max(...occupancyThisDay)); // Find the highest occupancy hour

    // Find the range starting and ending at 50% around the peak
    for (let j = peakHour; j >= 0; j--) {
        if (occupancyThisDay[j] < .5) break;
        peakStart = j;
    }
    for (let j = peakHour; j < occupancyThisDay.length; j++) {
        if (occupancyThisDay[j] < .5) break;
        peakEnd = j;
    }
    const peak_exists = peakStart !== null && peakEnd !== null

    let hoverInfo = [];

    // Add event count and occupancy percentage
    hoverInfo.push(`${event_count} Events`);
    hoverInfo.push(`${Math.round((1 - avgOccupancy) * 100)}% frei`)

    if (peak_exists) {
        const peakHoursText = `${String(peakStart).padStart(2, '0')}:00 - ${String(peakEnd).padStart(2, '0')}:00`;
        hoverInfo.push(`Peak: ${peakHoursText}`);
    }

    // Set the hover info by joining the array into a single string
    return hoverInfo.join(' | ');
}
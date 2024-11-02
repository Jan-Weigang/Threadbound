// let tables = [];
// let reservations = [];
// let eventTypes = [];

let reservationsUrl;
const daysContainer = document.getElementById('daysContainer');
const currentMonthDisplay = document.getElementById('currentMonth');
let currentDate = new Date();

document.addEventListener('DOMContentLoaded', function() {

    // Initial render
    renderCalendar(currentDate);

    // Navigation buttons
    document.getElementById('prevMonth').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(currentDate);
    });

    document.getElementById('nextMonth').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(currentDate);
    });
    document.getElementById('today').addEventListener('click', function() {
        const url = this.getAttribute('data-url');
        window.location.href = url;
    });
});


function renderCalendar(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    
    // Get the first day of the month
    const firstDayOfMonth = new Date(year, month, 1);
    const lastDayOfMonth = new Date(year, month + 1, 0);
    
    // Get the first day to display (considering the previous month)
    const firstDayToDisplay = new Date(firstDayOfMonth);
    firstDayToDisplay.setDate(firstDayOfMonth.getDate() - ((firstDayOfMonth.getDay() + 6) % 7));
    
    // Get the last day to display (considering the next month)
    const lastDayToDisplay = new Date(lastDayOfMonth);
    lastDayToDisplay.setDate(lastDayOfMonth.getDate() + (7 - lastDayOfMonth.getDay()));

    // Render the basic calendar structure (without reservations yet)
    updateCalendarUI(firstDayToDisplay, lastDayToDisplay, month, date);
    
    let viewType = 'regular';
    let requestStartDate = formatDateToYYYYMMDDLocal(firstDayToDisplay)
    let requestEndDate = formatDateToYYYYMMDDLocal(lastDayToDisplay)

    reservationsUrl = `/api/reservations/${viewType}?date=${requestStartDate}&end_date=${requestEndDate}`

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

        occupancyByDay= get_occupancy_by_day(reservations, tables)
        console.log("test");
        console.log(occupancyByDay);
        updateReservationsOnCalendar(reservations, eventTypes, firstDayToDisplay, lastDayToDisplay, month, occupancyByDay);

    }).catch(error => {
        console.error("Error fetching data:", error);
    });
    
}

function get_occupancy_by_day(reservations, tables) {
    totalTables = tables.length
    const totalCapacity = tables.reduce((sum, table) => sum + table.capacity, 0);


    // Step 1: Create an array to track bookings for each day and each hour
    const hoursRange = [...Array(12).keys()].map(i => i + 11); // Array from 12 to 23
    
    // Create a placeholder for each day of the month you're displaying
    const occupancyByDay = {}; // A map to store hourly bookings for each day

    reservations.forEach(reservation => {
        // Extract the start time and end time from the reservation
        const startHour = new Date(reservation.start_time).getHours();
        const endHour = new Date(reservation.end_time).getHours();
        const reservationDay = formatDateToYYYYMMDDLocal(new Date(reservation.start_time))

        // Find the table by its table_id in the tables array
        const table = tables.find(t => t.id === reservation.table_id);

        // Ensure the table exists before proceeding
        if (!table) {
            console.error(`Table with ID ${reservation.table_id} not found.`);
            return; // Skip this reservation if table is not found
        }

        if (!occupancyByDay[reservationDay]) {
            occupancyByDay[reservationDay] = Array(12).fill(0); // Initialize hourly bookings (12-23
        }

        const tableCapacity = table.capacity;
        for (let hour = Math.max(12, startHour); hour < Math.min(endHour, 23); hour++) {
            occupancyByDay[reservationDay][hour - 12] +=  tableCapacity / totalCapacity;
        }
    });

    return occupancyByDay;
}

function get_hover_info_for_dayElement(occupancyThisDay, event_count) {
    
    console.log(occupancyThisDay);
    const avgOccupancy = occupancyThisDay.reduce((a, b) => a + b, 0) / occupancyThisDay.length;

    // Determine peak hours based on 50% capacity
    let peakStart = null, peakEnd = null;
    const peakHour = occupancyThisDay.indexOf(Math.max(...occupancyThisDay)); // Find the highest occupancy hour

    console.log(peakHour);

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
        const peakHoursText = `${String(8 + peakStart).padStart(2, '0')}:00 - ${String(8 + peakEnd).padStart(2, '0')}:00`;
        hoverInfo.push(`Peak: ${peakHoursText}`);
    }

    // Set the hover info by joining the array into a single string
    return hoverInfo.join(' | ');
}






function updateReservationsOnCalendar(reservationData, eventTypes, firstDayToDisplay, lastDayToDisplay, month, occupancyByDay) {

    let day = new Date(firstDayToDisplay);
    const dayElements = daysContainer.querySelectorAll('.day');

    // Create a lookup for event type colors
    const eventTypeColorMap = {};
    eventTypes.forEach(eventType => {
        eventTypeColorMap[eventType.id] = eventType.color;
    });

    // Iterate through the displayed days
    for (let i = 0; i < dayElements.length; i++) {
        const dayElement = dayElements[i];

        const dayEvents = dayElement.querySelector('.day-events');

        const eventDateKey = dayElement.getAttribute('data-date');

        // Create the heat-bar-graph for each hour
        const heatBar = document.createElement('div');
        heatBar.className = 'heat-bar';

        const occupancyThisDay = occupancyByDay[eventDateKey] || Array(12).fill(0); // Fallback to an empty array with 13 zeroes

        // Calculate the gradient stops based on booked capacity vs total capacity with abrupt transitions
        const gradientStops = occupancyThisDay.map((percentageBooked, index) => {
            const start = (index / 12) * 100;
            const end = ((index + .3) / 12) * 100;
            const color = getHeatColor(percentageBooked);

            return `${color} ${start}%, ${color} ${end}%`; // Set abrupt color change between start and end
        }).join(',');


        // Apply the gradient to the heat bar
        heatBar.style.background = `linear-gradient(to right, ${gradientStops})`;


        const dayHeadingElement = dayElement.querySelector('.day-heading');

        // Append heat bar to the day's div
        dayHeadingElement.appendChild(heatBar);



        // Create a set to track unique events for this day
        const eventIdsForDay = new Set();

        // Iterate through the event data and add reservations to the corresponding day
        reservationData.forEach(reservation => {
            const eventDate = new Date(reservation.start_time);
            
            
            // Check if the event is on the current day
            if (eventDate.getFullYear() === day.getFullYear() &&
            eventDate.getMonth() === day.getMonth() &&
            eventDate.getDate() === day.getDate()) {
                
                // Only add the event if it hasn't been added already (check by event_id)
                if (!eventIdsForDay.has(reservation.event_id)) {
                    eventIdsForDay.add(reservation.event_id); // Add event_id to the set

                    // Create event block
                    const eventBlock = document.createElement('div');
                    eventBlock.classList.add('event');

                    // Set the color based on the event type color from the lookup map
                    const eventColor = eventTypeColorMap[reservation.event_type_id] || '#3788d8'; // Fallback color if none is provided
                    eventBlock.style.backgroundColor = eventColor;

                    // Set event info
                    eventBlock.innerHTML = '';

                    // Create a span for the event name
                    const eventNameSpan = document.createElement('span');
                    eventNameSpan.textContent = reservation.name;
                    eventNameSpan.classList.add('event-name')
                    eventBlock.appendChild(eventNameSpan);

                    // Create a span for the event time range (start and end times)
                    const eventTimeSpan = document.createElement('span');
                    eventTimeSpan.textContent = ` ${reservation.start_time.substring(11, 16)} - ${reservation.end_time.substring(11, 16)}`;
                    eventTimeSpan.classList.add('event-time')
                    eventBlock.appendChild(eventTimeSpan);

                    // Append event to the day
                    dayEvents.appendChild(eventBlock);
                }
            }
        });

        hoverInfo = get_hover_info_for_dayElement(occupancyThisDay, eventIdsForDay.size);
        dayElement.setAttribute('data-hover-info', hoverInfo);
        

        // Move to the next day
        day.setDate(day.getDate() + 1);
    }
}


function updateCalendarUI(firstDayToDisplay, lastDayToDisplay, month, date) {
    // Update the current month display
    currentMonthDisplay.textContent = date.toLocaleString('de-DE', { month: 'long', year: 'numeric' });

    // Clear previous days
    daysContainer.innerHTML = `<div class="day-header">Mo</div>
    <div class="day-header">Di</div>
    <div class="day-header">Mi</div>
    <div class="day-header">Do</div>
    <div class="day-header">Fr</div>
    <div class="day-header">Sa</div>
    <div class="day-header">So</div>`;

    // Get today's date
    const today = new Date();
    const todayYear = today.getFullYear();
    const todayMonth = today.getMonth();
    const todayDate = today.getDate();

    // Populate the days in the calendar (without reservations)
    let day = new Date(firstDayToDisplay);
    while (day <= lastDayToDisplay) {
        const dayElement = document.createElement('div');
        dayElement.classList.add('day');

        // Format the date in YYYY-MM-DD
        const formattedDate = formatDateToYYYYMMDDLocal(day);
        dayElement.setAttribute('data-date', formattedDate);

        
        // If day is in the current month, add a special class
        if (day.getMonth() === month) {
            dayElement.classList.add('current-month');
        } else {
            dayElement.classList.add('other-month');
        }

        // Add "current-day" class if the day is today
        if (day.getFullYear() === todayYear && day.getMonth() === todayMonth && day.getDate() === todayDate) {
            dayElement.classList.add('current-day');
        }


        dayHeadingDiv = document.createElement('div');
        dayHeadingDiv.classList.add('day-heading');
        
        weekDaySpan = document.createElement('span');
        const localDayString = day.toLocaleString('de-DE', { weekday: 'short' })
        weekDaySpan.textContent = localDayString; // 'Mo', 'Di', etc.
        weekDaySpan.classList.add('mobile-weekday');
        weekDaySpan.classList.add(localDayString.toLowerCase());
        dayHeadingDiv.appendChild(weekDaySpan); // TODO dayElement


        spanElement = document.createElement('span');
        spanElement.textContent = day.getDate();
        spanElement.classList.add('day-number')

        dayHeadingDiv.appendChild(spanElement);

        dayElement.appendChild(dayHeadingDiv);

        dayEventDiv = document.createElement('div');
        dayEventDiv.classList.add('day-events');

        dayElement.appendChild(dayEventDiv);


        // Capture the correct day value in a closure
        (function(currentDay) {
            dayElement.addEventListener('click', function() {
                const formattedDate = formatDateToYYYYMMDDLocal(currentDay); // Use local time formatting
                console.log(`Clicked on day: ${formattedDate}`);
                window.location.href = `/calendar/day?date=${formattedDate}`;
            });
        })(new Date(day)); // Passing a copy of the day to the closure

        // this needs to be added now, otherwise the eventlistener does not catch it. It is updated later.
        dayElement.setAttribute('data-hover-info', '');

        // Append the day element to the container
        daysContainer.appendChild(dayElement);

        // Move to the next day
        day.setDate(day.getDate() + 1);
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


function scrollToCurrentDay() {
    // Check if we're in mobile view
    if (window.innerWidth <= 768) {
        const currentDay = document.querySelector('.current-day');
        if (currentDay) {
            currentDay.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
        }
    }
}

// Run on load and on resize
window.addEventListener('load', scrollToCurrentDay);
window.addEventListener('resize', scrollToCurrentDay);
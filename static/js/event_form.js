// Initialize the time pickers
$('#startTime').mdtimepicker({
    theme: 'blue', 
    default: '17:00',
    is24hour: true
});
$('#endTime').mdtimepicker({
    theme: 'blue', 
    default: '19:00',
    is24hour: true
});

const isEditMode = document.getElementById('is-edit-mode').value === 'true';
const tableButtons = document.querySelectorAll('.table-button');
const hiddenInput = document.getElementById('table_ids');
const checkAvailabilityButton = document.getElementById('check-availability');
const eventData = document.getElementById('eventData');

document.addEventListener('DOMContentLoaded', function() {

    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    // - - - - - - - - - - SubmitButton Stuff - - - - - - - - - - - 
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

    // Reset the Checker when times are changed.
    updateSubmitButton();

    document.getElementById('date').addEventListener('change', function() {
        console.log("test");
        document.getElementById('submitButton').setAttribute('data-availability-checked', 'false');
        updateSubmitButton();
    });

    $('#startTime').on('timechanged', function(e) {
        console.log("test");
        document.getElementById('submitButton').setAttribute('data-availability-checked', 'false');
        updateSubmitButton();
    });

    $('#endTime').on('timechanged', function(e) {
        document.getElementById('submitButton').setAttribute('data-availability-checked', 'false');
        updateSubmitButton();
    });
    

    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    // - - - - - - - - - - Check Availability - - - - - - - - - - - 
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

    
    
    checkAvailabilityButton.addEventListener('click', function() {
        const date = document.getElementById('date').value;
        const startTime = document.getElementById('startTime').value;
        let endTime = document.getElementById('endTime').value;

        // Check if end time is set to 24:00 and adjust it to 23:59
        if (endTime === "00:00") {
            endTime = "23:59";
            document.getElementById('endTime').value = endTime; // Update the input field value
        }

        // Make an AJAX request to check availability
        fetch('/api/check_table_availability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date: date,
                start_time: startTime,
                end_time: endTime,
                exclude_event_id: isEditMode ? eventData.getAttribute('data-event-id') : null // Exclude current event in availability checks
            })
        })
        .then(response => response.json())
        .then(data => {
            // Update table buttons based on availability
            tableButtons.forEach(button => {
                const tableId = button.getAttribute('data-table-id');
                const tableData = data.tables.find(table => table.table_id == tableId);
                
                let earliestAvailability = tableData.earliest_available_start ? "Ab " + tableData.earliest_available_start : 'N/A';
                button.setAttribute('data-earliest-available', earliestAvailability);

                let latestAvailability = tableData.latest_possible_end ? "Bis " + tableData.latest_possible_end : 'N/A';
                button.setAttribute('data-latest-available', latestAvailability);


                if (tableData) {
                    const selectedStartTime = startTime;
                    const selectedEndTime = endTime;

                    if (!tableData.available) {
                        // button.disabled = true;

                        button.select = false; // if it was selected, add flash effect
                        if (button.classList.contains('selected')) {
                            button.classList.remove('selected');
                        
                            // Flash red
                            button.classList.add('flash-unselect');
                            setTimeout(() => button.classList.remove('flash-unselect'), 4000);
                        }

                        button.classList.add('unavailable');

                        button.setAttribute('title', `Available from ${tableData.earliest_available_start || 'N/A'} to ${tableData.latest_possible_end || 'N/A'}`);
                    
                        // Add bold class to ::before or ::after elements if current selection is the reason for unavailability
                        if (tableData.earliest_available_start && selectedStartTime <= tableData.earliest_available_start) {
                            button.classList.add('bold-earliest');
                        } else {
                            button.classList.remove('bold-earliest');
                        }

                        if (tableData.latest_possible_end && selectedEndTime >= tableData.latest_possible_end) {
                            button.classList.add('bold-latest');
                        } else {
                            button.classList.remove('bold-latest');
                        }

                    
                    } else {
                        button.disabled = false;
                        button.classList.remove('unavailable');
                        button.removeAttribute('title');
                        button.classList.remove('bold-latest');
                        button.classList.remove('bold-earliest');
                    }
                }

                document.getElementById('submitButton').setAttribute('data-availability-checked', 'true');
                document.getElementById('submitButton').setAttribute('data-collision', 'false');
                updateSubmitButton();
                updateSelectedTables();
            });
        });
    });


    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    // - - - - - - - - Updating Table Button Grid - - - - - - - - - 
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 


    tableButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Toggle the selected class
            button.classList.toggle('selected');

            let hasUnavailableSelected = document.querySelector('.table-button.unavailable.selected') !== null;
            // Update submitButton data attribute
            let submitButton = document.getElementById('submitButton');
            if (hasUnavailableSelected) {
                submitButton.setAttribute('data-collision', 'true');
                submitButton.setAttribute('data-availability-checked', 'false');
            }
            
            
            // Update the hidden input with selected table IDs
            updateSelectedTables();
        });
    });

    
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    // - - - - - - - - Updating Selection colors - - - - - - - - - -
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

    // Get all option elements with the data-color attribute
    const optionElements = document.querySelectorAll('option[data-color]');
        
    // Loop through each option and apply the background color
    optionElements.forEach(function(option) {
        const color = option.getAttribute('data-color');  // Get the color value from data-color
        option.style.backgroundColor = color;  // Set the background color
    });

    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    // - - - - - - - - Updating Eventy Type Icons - - - - - - - - - 
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

    const dateInput = document.getElementById('date');
    // Retrieve the data-date and data-requested-date values
    const eventDate = eventData.getAttribute('data-date');
    const requestedDate = eventData.getAttribute('data-requested-date');

    // Set the value of dateInput based on the conditions
    if (eventDate) {
        dateInput.value = eventDate;
        console.log("eventDate");
    } else if (requestedDate) {
        dateInput.value = requestedDate;
        console.log("requested");
    } else {
        // If neither are set, use today's date
        const today = new Date().toISOString().split('T')[0]; // Get the current date in YYYY-MM-DD format
        dateInput.value = today;
        console.log("today");
    }

    // Handle icon for Game Category select box
    const gameCategorySelect = document.getElementById('game_category_id');
    const iconPreview = document.getElementById('icon-preview');
    updateSelectIcon(gameCategorySelect, iconPreview);

    gameCategorySelect.addEventListener('change', function() {
        updateSelectIcon(gameCategorySelect, iconPreview);
    });


    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    // - - - - - - - - - - Updating Event Colors - - - - - - - - - -
    // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

    // Fetch event type colors and style the options
    fetch('/api/event-types')
        .then(response => response.json())
        .then(data => {
            const eventTypeSelect = document.getElementById('event_type_id');
            Array.from(eventTypeSelect.options).forEach(option => {
                const eventTypeId = option.value;
                if (data[eventTypeId]) {
                    option.style.backgroundColor = data[eventTypeId];
                    option.setAttribute('data-color', data[eventTypeId]);
                }
            });

            // Set the select box background to the color of the selected option
            updateSelectColor(eventTypeSelect);
        });

    // Change select color based on user selection
    const eventTypeSelect = document.getElementById('event_type_id');
    eventTypeSelect.addEventListener('change', function() {
        updateSelectColor(eventTypeSelect);
    });


});

// Function to update the select background color based on the selected option
function updateSelectColor(selectElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const color = selectedOption.getAttribute('data-color');
    if (color) {
        selectElement.style.backgroundColor = color;
    } else {
        selectElement.style.backgroundColor = '';
    }
}

// Form validation to ensure end time is after start time
document.querySelector('form').addEventListener('submit', function(event) {
    const startTime = document.getElementById('startTime').value;
    let endTime = document.getElementById('endTime').value;

    // Check if end time is set to 24:00 and adjust it to 23:59
    if (endTime === "00:00") {
        endTime = "23:59";
        document.getElementById('endTime').value = endTime; // Update the input field value
    }


    if (startTime >= endTime) {
        alert("End Time must be later than Start Time.");
        event.preventDefault(); // Prevent form submission if validation fails
    }
});






// Function to update the SVG icon for the select element
function updateSelectIcon(selectElement, iconElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const base64Svg = selectedOption.getAttribute('data-icon');

    if (base64Svg) {
        const decodedSvg = atob(base64Svg);
        iconElement.innerHTML = decodedSvg;
    } else {
        iconElement.innerHTML = '';
    }
}

window.updateSelectedTables = function() {
    console.log("updating selected tabels");
    let selectedTableIds = Array.from(document.querySelectorAll('.table-button.selected'))
        .map(button => button.getAttribute('data-table-id'));
    hiddenInput.value = selectedTableIds.join(',');

    // Set the data attribute on the submit button
    let submitButton = document.getElementById('submitButton');
    submitButton.setAttribute('data-tables', selectedTableIds.length > 0 ? 'true' : 'false');

    // Run the checker function
    updateSubmitButton();
    
}


function updateSubmitButton() {
    const submitButton = document.getElementById('submitButton');
    const requestButton = document.getElementById('requestButton');
    let tablesSelected = submitButton.getAttribute('data-tables') === 'true';
    let availabilityChecked = submitButton.getAttribute('data-availability-checked') === 'true';
    let collisionCheck = submitButton.getAttribute('data-collision') === 'true';

    if (tablesSelected && availabilityChecked) {
        submitButton.removeAttribute('disabled'); // Explicitly remove the disabled attribute
        submitButton.classList.remove('unavailable');
        submitButton.textContent = "Tische buchen!";

    } else {
        submitButton.setAttribute('disabled', 'disabled'); // Set the disabled attribute when no tables are selected
        submitButton.classList.add('unavailable');
        submitButton.textContent = "Prüfe, bevor du buchen kannst";
    }

    if (collisionCheck) {
        requestButton.style.display = 'block';
    } else {
        requestButton.style.display = 'none';
    }
}

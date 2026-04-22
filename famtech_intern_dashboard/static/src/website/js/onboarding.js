document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('meetingSearch');
    const eventFilter = document.getElementById('eventFilter');
    const attendanceFilter = document.getElementById('attendanceFilter');
    const orderSelect = document.getElementById('dateOrder');
    const eventsGrid = document.getElementById('eventsGrid');
    const noResults = document.getElementById('noResults');
    const cards = Array.from(document.querySelectorAll('.event-card-wrapper'));

    function filterEvents() {
        const searchTerm = searchInput.value.toLowerCase();
        const eventStatus = eventFilter.value;
        const attendanceStatus = attendanceFilter.value;
        const order = orderSelect.value;

        let visibleCount = 0;

        cards.forEach(card => {
            const name = card.getAttribute('data-name');
            const status = card.getAttribute('data-status');
            const attendance = card.getAttribute('data-attendance');

            const matchesSearch = name.includes(searchTerm);
            const matchesEvent = eventStatus === 'all' || status === eventStatus;
            const matchesAttendance = attendanceStatus === 'all' || attendance === attendanceStatus;

            const isVisible = matchesSearch && matchesEvent && matchesAttendance;

            if (isVisible) {
                card.classList.remove('d-none');
                visibleCount++;
            } else {
                card.classList.add('d-none');
            }
        });

        // Sort
        const sortedCards = cards
            .filter(c => !c.classList.contains('d-none'))
            .sort((a, b) => {
                const timeA = Number(a.getAttribute('data-timestamp'));
                const timeB = Number(b.getAttribute('data-timestamp'));

                return order === 'asc' ? timeA - timeB : timeB - timeA;
            });

        sortedCards.forEach(card => eventsGrid.appendChild(card));

        // Empty State
        if (visibleCount === 0 && cards.length > 0) {
            noResults.classList.remove('d-none');
        } else {
            noResults.classList.add('d-none');
        }
    }

    searchInput.addEventListener('input', filterEvents);
    eventFilter.addEventListener('change', filterEvents);
    attendanceFilter.addEventListener('change', filterEvents);
    orderSelect.addEventListener('change', filterEvents);
});

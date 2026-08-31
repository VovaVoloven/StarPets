// --- JavaScript for handling bookmark toggling and rating ---
// Wait for the page to fully load
document.addEventListener('DOMContentLoaded', function () {

    const buttons = document.querySelectorAll('.toggle-bookmark-btn');

    // --- BOOKMARK LOGIC ---
    buttons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();

            const petId = this.getAttribute('data-pet-id');
            const btn = this;

            fetch(`${BOOKMARK_URL}${petId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
                .then(response => {
                    if (!response.ok) { throw new Error(`HTTP error! status: ${response.status}`); }
                    return response.json();
                })
                .then(data => {
                    if (typeof data.is_bookmarked !== 'undefined') {
                        if (data.is_bookmarked === true || data.is_bookmarked === true) {
                            button.className = 'btn-icon-action btn-unbookmark toggle-bookmark-btn';
                            button.title = 'Unbookmark';
                            button.innerHTML = `
                                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"></path>
                                    <line x1="2" x2="22" y1="2" y2="22" stroke="white" stroke-width="3"></line>
                                    <line x1="2" x2="22" y1="2" y2="22" stroke="#f59e0b" stroke-width="1"></line>
                                </svg>
                            `;
                        } else {
                            button.className = 'btn-icon-action btn-bookmark toggle-bookmark-btn';
                            button.title = 'Bookmark';
                            button.innerHTML = `
                                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"></path>
                                </svg>
                            `;
                        }
                    } else {
                        console.error("Backend did not return 'is_bookmarked'.", data);
                    }
                })
                .catch(error => console.error('Fetch Error:', error));
        });
    });

    // --- RATING LOGIC ---
    const ratingContainers = document.querySelectorAll('.interactive-rating');

    ratingContainers.forEach(container => {
        const stars = container.querySelectorAll('.star');
        const userRatingText = container.querySelector('.user-rating-text');
        const petId = container.getAttribute('data-pet-id');
        let currentUserRating = parseInt(container.getAttribute('data-user-rating')) || 0;

        // Function to color stars based on rating and state (hover vs saved)
        const updateStars = (rating, isHover = false) => {
            stars.forEach(star => {
                const starVal = parseInt(star.getAttribute('data-val'));
                if (starVal <= rating) {
                    // Light yellow for hover, gold for saved
                    star.style.color = isHover ? '#fde047' : '#f59e0b'; 
                } else {
                    star.style.color = '#e5e7eb'; // Grey
                }
            });
            userRatingText.textContent = `(${rating}/5)`;
        };

        stars.forEach(star => {
            // Hover Effect: Highlight stars up to the hovered star
            star.addEventListener('mouseenter', function() {
                const hoverVal = parseInt(this.getAttribute('data-val'));
                updateStars(hoverVal, true);
            });

            // Click Effect: Submit via AJAX
            star.addEventListener('click', function() {
                const newRating = parseInt(this.getAttribute('data-val'));

                fetch(`${RATE_URL}${petId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ 'rating': newRating })
                })
                // Expecting a JSON response with at least { success: true, new_average: 4.2 }
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Instantly update the saved User Rating
                        currentUserRating = newRating;
                        container.setAttribute('data-user-rating', currentUserRating);
                        updateStars(currentUserRating, false); 

                        // Instantly update the Average Rating visuals below it
                        const goldStarsOverlay = container.querySelector('.gold-stars-overlay');
                        const fillPercentage = (data.new_average / 5.0) * 100;
                        goldStarsOverlay.style.width = `${fillPercentage}%`;

                        // Update the numeric average rating text as well
                        const avgRatingText = container.querySelector('.rating-text');
                        avgRatingText.textContent = `(${data.new_average.toFixed(1)}/5.0)`;
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        });

        // Mouse Leave Effect: Reset back to the saved rating
        const userRatingContainer = container.querySelector('.user-rating-container');
        userRatingContainer.addEventListener('mouseleave', function() {
            updateStars(currentUserRating, false);
        });
    });

    // close menu if click outside it
    //window.addEventListener('click', (e) => {
        //if (dropDownMenu.classList.contains('show')){
         //   dropDownMenu.classList.remove('show');
        //}
    //});

    // --- CATEGORY FILTER LOGIC ---
    const filterItems = document.querySelectorAll('.category-filter-item');
    const categoryInput = document.getElementById('category-input');
    const filterForm = document.getElementById('filter-form');

    // Only run this script if we are actually on the Categories page
    if (filterItems.length > 0 && categoryInput && filterForm) {
        filterItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault(); // Stops the page from jumping to the top from the href="#"
                
                // Get the value from the data attribute and submit
                const value = this.getAttribute('data-value');
                categoryInput.value = value;
                filterForm.submit();
            });
        });
    }

});


// --- Stnadart Django Helper function to manage cookies ---
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;

}



// ------ toggle profile description edit --------------



// ----clickable card on home page ------

document.addEventListener('DOMContentLoaded', function() {
    // Select all cards with the clickable class
    const clickableCards = document.querySelectorAll('.clickable-card');

    clickableCards.forEach(card => {
        card.addEventListener('click', function() {
            // Get the URL from the data-url attribute
            const targetUrl = this.getAttribute('data-url');
            if (targetUrl) {
                window.location.href = targetUrl;
            }
        });
    });
});

function toggleBioEdit(buttonElement, profileEditUrl) {
    const bioBox = document.getElementById('bio-editor');
    const editBtn = buttonElement
    const csrfToken = getCookie('csrftoken');
    const placeholderText = "Click 'Edit Bio' to write your description!"

    if (bioBox.contentEditable === "false") {
        //if initial text present, removes it for user to put their own
        // , otherwise, users text stays
        if (bioBox.innerText.trim() == placeholderText) {
            bioBox.innerText = "";
        }

        bioBox.contentEditable = "true";
        bioBox.classList.add("bg-white", "border-warning");
        bioBox.focus();
        editBtn.innerText = "SAVE CHANGES";
        editBtn.classList.replace("btn-outline-secondary", "btn-amber");
    } else {
        //save mode
        const newBio = bioBox.innerText.trim();

        fetch(profileEditUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-with": "XMLHttpRequest"
            },
            body: new URLSearchParams({"description": newBio})
        })
        .then(response => {
            if (response.ok) {
                bioBox.contentEditable = "false";
                bioBox.classList.remove("bg-white", "border-warning");
                editBtn.innerText = "EDIT BIO";
                editBtn.classList.replace("btn-amber", "btn-outline-secondary");

                if (newBio === ""){
                    bioBox.innerText = placeholderText;
                }
            } else {
                alert("Error saving bio.");
                        }
        })
        .catch(error => console.error('Bio Update Error:', error));
    }
}

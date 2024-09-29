const words = ['Father', 'Product Manager', 'Procrastinator', 'Photographer', 'Musician', 'Chef', 'Snowboarder', 'Lover'];
        const typewriterElement = document.getElementById('typewriter');
        let wordIndex = 0;
        let charIndex = 0;
        let isDeleting = false;

        function typeEffect() {
            const currentWord = words[wordIndex];
            const shouldSwitch = isDeleting && charIndex === 0;

            if (shouldSwitch) {
                isDeleting = false;
                wordIndex = (wordIndex + 1) % words.length;
            } else if (!isDeleting && charIndex === currentWord.length) {
                isDeleting = true;
                setTimeout(typeEffect, 1000); // Pause before starting to delete
                return;
            }

            typewriterElement.textContent = currentWord.substring(0, charIndex);

            charIndex += isDeleting ? -1 : 1;

            const typingSpeed = isDeleting ? 50 : 150; // Faster deletion
            setTimeout(typeEffect, typingSpeed);
        }

        document.addEventListener('DOMContentLoaded', typeEffect);

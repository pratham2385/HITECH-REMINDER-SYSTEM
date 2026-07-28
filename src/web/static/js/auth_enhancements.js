const AUTH_QUOTES = [
  {
    "text": "The best way to predict the future is to invent it.",
    "author": "Alan Kay"
  },
  {
    "text": "Innovation distinguishes between a leader and a follower.",
    "author": "Steve Jobs"
  },
  {
    "text": "Simplicity is the ultimate sophistication.",
    "author": "Leonardo da Vinci"
  },
  {
    "text": "First, solve the problem. Then, write the code.",
    "author": "John Johnson"
  },
  {
    "text": "Make it work, make it right, make it fast.",
    "author": "Kent Beck"
  },
  {
    "text": "Before software can be reusable it first has to be usable.",
    "author": "Ralph Johnson"
  },
  {
    "text": "Code is like humor. When you have to explain it, it\u2019s bad.",
    "author": "Cory House"
  },
  {
    "text": "Optimism is an occupational hazard of programming: feedback is the treatment.",
    "author": "Kent Beck"
  },
  {
    "text": "In some ways, programming is like painting. You start with a blank canvas and certain basic raw materials.",
    "author": "Andrew Hunt"
  },
  {
    "text": "The only way to do great work is to love what you do.",
    "author": "Steve Jobs"
  },
  {
    "text": "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "author": "Winston Churchill"
  },
  {
    "text": "It always seems impossible until it is done.",
    "author": "Nelson Mandela"
  },
  {
    "text": "The secret of getting ahead is getting started.",
    "author": "Mark Twain"
  },
  {
    "text": "Quality is not an act, it is a habit.",
    "author": "Aristotle"
  },
  {
    "text": "Discipline is the bridge between goals and accomplishment.",
    "author": "Jim Rohn"
  },
  {
    "text": "I have not failed. I've just found 10,000 ways that won't work.",
    "author": "Thomas A. Edison"
  },
  {
    "text": "If you think good architecture is expensive, try bad architecture.",
    "author": "Brian Foote"
  },
  {
    "text": "A good programmer is someone who always looks both ways before crossing a one-way street.",
    "author": "Doug Linder"
  },
  {
    "text": "Testing leads to failure, and failure leads to understanding.",
    "author": "Burt Rutan"
  },
  {
    "text": "We build our computer (systems) the way we build our cities: over time, without a plan, on top of ruins.",
    "author": "Ellen Ullman"
  },
  {
    "text": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",
    "author": "Martin Fowler"
  },
  {
    "text": "Software and cathedrals are much the same \u2013 first we build them, then we pray.",
    "author": "Sam Ewing"
  },
  {
    "text": "Programs must be written for people to read, and only incidentally for machines to execute.",
    "author": "Harold Abelson"
  },
  {
    "text": "Always code as if the guy who ends up maintaining your code will be a violent psychopath who knows where you live.",
    "author": "John Woods"
  },
  {
    "text": "There are two hard things in computer science: cache invalidation, naming things, and off-by-one errors.",
    "author": "Phil Karlton"
  },
  {
    "text": "Talk is cheap. Show me the code.",
    "author": "Linus Torvalds"
  },
  {
    "text": "Perfection (in design) is achieved not when there is nothing more to add, but rather when there is nothing more to take away.",
    "author": "Antoine de Saint-Exup\u00e9ry"
  },
  {
    "text": "Learning never exhausts the mind.",
    "author": "Leonardo da Vinci"
  },
  {
    "text": "Technology is best when it brings people together.",
    "author": "Matt Mullenweg"
  },
  {
    "text": "What you do today can improve all your tomorrows.",
    "author": "Ralph Marston"
  },
  {
    "text": "Don't watch the clock; do what it does. Keep going.",
    "author": "Sam Levenson"
  },
  {
    "text": "You don't have to be great to start, but you have to start to be great.",
    "author": "Zig Ziglar"
  },
  {
    "text": "Success usually comes to those who are too busy to be looking for it.",
    "author": "Henry David Thoreau"
  },
  {
    "text": "The future depends on what you do today.",
    "author": "Mahatma Gandhi"
  },
  {
    "text": "The most difficult thing is the decision to act, the rest is merely tenacity.",
    "author": "Amelia Earhart"
  },
  {
    "text": "Everything you've ever wanted is on the other side of fear.",
    "author": "George Addair"
  },
  {
    "text": "There are no secrets to success. It is the result of preparation, hard work, and learning from failure.",
    "author": "Colin Powell"
  },
  {
    "text": "Success is walking from failure to failure with no loss of enthusiasm.",
    "author": "Winston Churchill"
  },
  {
    "text": "Action is the foundational key to all success.",
    "author": "Pablo Picasso"
  },
  {
    "text": "Do one thing every day that scares you.",
    "author": "Eleanor Roosevelt"
  },
  {
    "text": "What seems to us as bitter trials are often blessings in disguise.",
    "author": "Oscar Wilde"
  },
  {
    "text": "The distance between insanity and genius is measured only by success.",
    "author": "Bruce Feirstein"
  },
  {
    "text": "When you stop chasing the wrong things, you give the right things a chance to catch you.",
    "author": "Lolly Daskal"
  },
  {
    "text": "To live a creative life, we must lose our fear of being wrong.",
    "author": "Joseph Chilton Pearce"
  },
  {
    "text": "If you are not willing to risk the usual, you will have to settle for the ordinary.",
    "author": "Jim Rohn"
  },
  {
    "text": "Motivation is what gets you started. Habit is what keeps you going.",
    "author": "Jim Ryun"
  },
  {
    "text": "Success is the sum of small efforts, repeated day-in and day-out.",
    "author": "Robert Collier"
  },
  {
    "text": "Don't let yesterday take up too much of today.",
    "author": "Will Rogers"
  },
  {
    "text": "It's not whether you get knocked down, it's whether you get up.",
    "author": "Vince Lombardi"
  },
  {
    "text": "If you are working on something that you really care about, you don't have to be pushed. The vision pulls you.",
    "author": "Steve Jobs"
  },
  {
    "text": "People who are crazy enough to think they can change the world, are the ones who do.",
    "author": "Rob Siltanen"
  },
  {
    "text": "Failure will never overtake me if my determination to succeed is strong enough.",
    "author": "Og Mandino"
  },
  {
    "text": "Entrepreneurs are great at dealing with uncertainty and also very good at minimizing risk. That's the classic entrepreneur.",
    "author": "Mohnish Pabrai"
  },
  {
    "text": "We may encounter many defeats but we must not be defeated.",
    "author": "Maya Angelou"
  },
  {
    "text": "Knowing is not enough; we must apply. Wishing is not enough; we must do.",
    "author": "Johann Wolfgang Von Goethe"
  },
  {
    "text": "Imagine your life is perfect in every respect; what would it look like?",
    "author": "Brian Tracy"
  },
  {
    "text": "We generate fears while we sit. We overcome them by action.",
    "author": "Dr. Henry Link"
  },
  {
    "text": "Whether you think you can or think you can't, you're right.",
    "author": "Henry Ford"
  },
  {
    "text": "Security is mostly a superstition. Life is either a daring adventure or nothing.",
    "author": "Helen Keller"
  },
  {
    "text": "The man who has confidence in himself gains the confidence of others.",
    "author": "Hasidic Proverb"
  },
  {
    "text": "The only limit to our realization of tomorrow will be our doubts of today.",
    "author": "Franklin D. Roosevelt"
  },
  {
    "text": "Creativity is intelligence having fun.",
    "author": "Albert Einstein"
  },
  {
    "text": "What you lack in talent can be made up with desire, hustle and giving 110% all the time.",
    "author": "Don Zimmer"
  },
  {
    "text": "Do what you can with all you have, wherever you are.",
    "author": "Theodore Roosevelt"
  },
  {
    "text": "Develop an 'attitude of gratitude'. Say thank you to everyone you meet for everything they do for you.",
    "author": "Brian Tracy"
  },
  {
    "text": "You are never too old to set another goal or to dream a new dream.",
    "author": "C.S. Lewis"
  },
  {
    "text": "To see what is right and not do it is a lack of courage.",
    "author": "Confucius"
  },
  {
    "text": "Reading is to the mind, as exercise is to the body.",
    "author": "Brian Tracy"
  },
  {
    "text": "Fake it until you make it! Act as if you had all the confidence you require until it becomes your reality.",
    "author": "Brian Tracy"
  },
  {
    "text": "The future belongs to the competent. Get good, get better, be the best!",
    "author": "Brian Tracy"
  },
  {
    "text": "For every reason it's not possible, there are hundreds of people who have faced the same circumstances and succeeded.",
    "author": "Jack Canfield"
  },
  {
    "text": "Things work out best for those who make the best of how things work out.",
    "author": "John Wooden"
  },
  {
    "text": "A room without books is like a body without a soul.",
    "author": "Marcus Tullius Cicero"
  },
  {
    "text": "I think goals should never be easy, they should force you to work, even if they are uncomfortable at the time.",
    "author": "Michael Phelps"
  },
  {
    "text": "One of the lessons that I grew up with was to always stay true to yourself and never let what somebody else says distract you from your goals.",
    "author": "Michelle Obama"
  },
  {
    "text": "Today's accomplishments were yesterday's impossibilities.",
    "author": "Robert H. Schuller"
  },
  {
    "text": "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle.",
    "author": "Steve Jobs"
  },
  {
    "text": "You don't have to be great to start, but you have to start to be great.",
    "author": "Zig Ziglar"
  },
  {
    "text": "A clear vision, backed by definite plans, gives you a tremendous feeling of confidence and personal power.",
    "author": "Brian Tracy"
  },
  {
    "text": "There are no limits to what you can accomplish, except the limits you place on your own thinking.",
    "author": "Brian Tracy"
  },
  {
    "text": "It is our attitude at the beginning of a difficult task which, more than anything else, will affect its successful outcome.",
    "author": "William James"
  },
  {
    "text": "You miss 100% of the shots you don't take.",
    "author": "Wayne Gretzky"
  },
  {
    "text": "The most difficult thing is the decision to act, the rest is merely tenacity.",
    "author": "Amelia Earhart"
  },
  {
    "text": "Every strike brings me closer to the next home run.",
    "author": "Babe Ruth"
  },
  {
    "text": "Definiteness of purpose is the starting point of all achievement.",
    "author": "W. Clement Stone"
  },
  {
    "text": "We must balance conspicuous consumption with conscious capitalism.",
    "author": "Kevin Kruse"
  },
  {
    "text": "Life is what happens to you while you're busy making other plans.",
    "author": "John Lennon"
  },
  {
    "text": "We become what we think about.",
    "author": "Earl Nightingale"
  },
  {
    "text": "Twenty years from now you will be more disappointed by the things that you didn't do than by the ones you did do.",
    "author": "Mark Twain"
  },
  {
    "text": "Life is 10% what happens to me and 90% of how I react to it.",
    "author": "Charles Swindoll"
  },
  {
    "text": "The most common way people give up their power is by thinking they don't have any.",
    "author": "Alice Walker"
  },
  {
    "text": "The mind is everything. What you think you become.",
    "author": "Buddha"
  },
  {
    "text": "The best time to plant a tree was 20 years ago. The second best time is now.",
    "author": "Chinese Proverb"
  },
  {
    "text": "An unexamined life is not worth living.",
    "author": "Socrates"
  },
  {
    "text": "Eighty percent of success is showing up.",
    "author": "Woody Allen"
  },
  {
    "text": "Your time is limited, so don't waste it living someone else's life.",
    "author": "Steve Jobs"
  },
  {
    "text": "Winning isn't everything, but wanting to win is.",
    "author": "Vince Lombardi"
  }
];

function initTypewriter() {
  const titleEl = document.getElementById('typewriter-title');
  if (!titleEl) return;

  const text = "Welcome to\nHiTech Automated Reminder System";
  let i = 0;
  titleEl.innerHTML = '<span id="tw-text"></span><span class="typewriter-cursor"></span>';
  const textEl = document.getElementById('tw-text');

  const speed = 40; // Approx 2-4 seconds for 45 chars is ~40-80ms per char

  function typeWriter() {
    if (i < text.length) {
      if (text.charAt(i) === '\n') {
        textEl.innerHTML += '<br>';
      } else {
        textEl.innerHTML += text.charAt(i);
      }
      i++;
      setTimeout(typeWriter, speed);
    }
  }

  // Start after a tiny delay
  setTimeout(typeWriter, 300);
}

function initQuoteSystem() {
  const container = document.getElementById('daily-quote-container');
  if (!container) return;

  const today = new Date().toDateString();
  const storedDate = localStorage.getItem('authQuoteDate');
  let storedQuoteIndex = localStorage.getItem('authQuoteIndex');
  let usedQuotes = JSON.parse(localStorage.getItem('authUsedQuotes') || '[]');

  let quoteToDisplay;

  if (storedDate === today && storedQuoteIndex !== null) {
    // Same day, use same quote
    quoteToDisplay = AUTH_QUOTES[parseInt(storedQuoteIndex, 10)];
  } else {
    // New day, pick new quote
    let availableIndices = [];
    for (let i = 0; i < AUTH_QUOTES.length; i++) {
      if (!usedQuotes.includes(i)) availableIndices.push(i);
    }

    // Reset if all used
    if (availableIndices.length === 0) {
      usedQuotes = [];
      for (let i = 0; i < AUTH_QUOTES.length; i++) availableIndices.push(i);
    }

    // Pick random from available
    const randomIndex = availableIndices[Math.floor(Math.random() * availableIndices.length)];
    quoteToDisplay = AUTH_QUOTES[randomIndex];

    // Save state
    usedQuotes.push(randomIndex);
    localStorage.setItem('authUsedQuotes', JSON.stringify(usedQuotes));
    localStorage.setItem('authQuoteIndex', randomIndex.toString());
    localStorage.setItem('authQuoteDate', today);
  }

  if (quoteToDisplay) {
    container.innerHTML = `
            <div class="quote-text">"${quoteToDisplay.text}"</div>
            <div class="quote-author">— ${quoteToDisplay.author}</div>
        `;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initTypewriter();
  initQuoteSystem();
});

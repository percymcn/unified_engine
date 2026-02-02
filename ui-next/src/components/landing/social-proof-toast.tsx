"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, MapPin } from "lucide-react";

// Sample first names for variety
const firstNames = [
  "James", "Michael", "David", "John", "Robert", "William", "Thomas", "Daniel",
  "Sarah", "Emma", "Jessica", "Ashley", "Amanda", "Jennifer", "Lisa", "Emily",
  "Chris", "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Jamie", "Riley",
  "Marcus", "Andre", "Carlos", "Ahmed", "Wei", "Raj", "Yuki", "Omar"
];

// Plans with their display info
const plans = [
  { name: "Starter", color: "text-blue-500" },
  { name: "Trader", color: "text-emerald-500" },
  { name: "Pro", color: "text-purple-500" },
];

// Nearby cities by major cities (for IP-based location)
const nearbyCities: Record<string, string[]> = {
  // US Cities
  "New York": ["Brooklyn", "Jersey City", "Newark", "Queens", "Hoboken", "Manhattan"],
  "Los Angeles": ["Santa Monica", "Pasadena", "Long Beach", "Glendale", "Burbank", "Irvine"],
  "Chicago": ["Naperville", "Evanston", "Oak Park", "Schaumburg", "Aurora"],
  "Houston": ["Sugar Land", "The Woodlands", "Katy", "Pearland", "Pasadena"],
  "Phoenix": ["Scottsdale", "Mesa", "Tempe", "Chandler", "Gilbert"],
  "Dallas": ["Fort Worth", "Plano", "Irving", "Arlington", "Frisco"],
  "San Francisco": ["Oakland", "Berkeley", "San Jose", "Palo Alto", "Fremont"],
  "Seattle": ["Bellevue", "Tacoma", "Redmond", "Kirkland", "Everett"],
  "Miami": ["Fort Lauderdale", "Boca Raton", "West Palm Beach", "Coral Gables"],
  "Atlanta": ["Marietta", "Decatur", "Sandy Springs", "Alpharetta", "Roswell"],
  "Boston": ["Cambridge", "Somerville", "Brookline", "Newton", "Quincy"],
  "Denver": ["Aurora", "Boulder", "Lakewood", "Littleton", "Arvada"],
  // Canada
  "Toronto": ["Mississauga", "Brampton", "Markham", "Vaughan", "Scarborough"],
  "Vancouver": ["Burnaby", "Richmond", "Surrey", "North Vancouver", "Coquitlam"],
  // UK
  "London": ["Westminster", "Camden", "Greenwich", "Croydon", "Hackney", "Islington"],
  "Manchester": ["Salford", "Stockport", "Bolton", "Oldham", "Trafford"],
  // Europe
  "Paris": ["Boulogne", "Saint-Denis", "Versailles", "Nanterre", "Montreuil"],
  "Berlin": ["Potsdam", "Spandau", "Charlottenburg", "Kreuzberg", "Mitte"],
  "Amsterdam": ["Rotterdam", "The Hague", "Utrecht", "Haarlem", "Almere"],
  // Asia Pacific
  "Sydney": ["Parramatta", "North Sydney", "Bondi", "Manly", "Chatswood"],
  "Singapore": ["Orchard", "Marina Bay", "Jurong", "Tampines", "Woodlands"],
  "Tokyo": ["Shibuya", "Shinjuku", "Ginza", "Akihabara", "Roppongi"],
  "Hong Kong": ["Kowloon", "Central", "Tsim Sha Tsui", "Causeway Bay", "Mong Kok"],
  "Dubai": ["Abu Dhabi", "Sharjah", "Jumeirah", "Downtown Dubai", "Marina"],
  "Mumbai": ["Thane", "Navi Mumbai", "Andheri", "Bandra", "Powai"],
};

// Fallback cities by country
const citiesByCountry: Record<string, string[]> = {
  "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Dallas", "Miami", "Atlanta", "Boston", "Denver", "Seattle", "San Francisco"],
  "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton"],
  "GB": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool"],
  "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
  "DE": ["Berlin", "Munich", "Frankfurt", "Hamburg", "Cologne"],
  "FR": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice"],
  "NL": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht"],
  "SG": ["Singapore", "Orchard", "Marina Bay", "Jurong"],
  "AE": ["Dubai", "Abu Dhabi", "Sharjah"],
  "IN": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad"],
  "JP": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Kyoto"],
  "HK": ["Hong Kong", "Kowloon", "Central"],
  "Default": ["New York", "London", "Singapore", "Sydney", "Toronto", "Dubai"]
};

// Time ago strings
const timeAgoOptions = [
  "just now",
  "1 minute ago",
  "2 minutes ago",
  "3 minutes ago",
  "5 minutes ago",
  "8 minutes ago",
  "12 minutes ago",
];

interface UserLocation {
  city: string;
  country: string;
  nearbyCities: string[];
}

interface PurchaseNotification {
  id: number;
  name: string;
  location: string;
  plan: typeof plans[number];
  timeAgo: string;
}

function getRandomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateNotification(id: number, userLocation: UserLocation): PurchaseNotification {
  // Use nearby cities if available, otherwise use country's cities
  const locations = userLocation.nearbyCities.length > 0
    ? userLocation.nearbyCities
    : citiesByCountry[userLocation.country] || citiesByCountry["Default"];

  return {
    id,
    name: getRandomItem(firstNames),
    location: getRandomItem(locations),
    plan: getRandomItem(plans),
    timeAgo: getRandomItem(timeAgoOptions),
  };
}

async function fetchUserLocation(): Promise<UserLocation> {
  try {
    // Use ipapi.co for free IP geolocation (no API key needed, 1000/day limit)
    const response = await fetch("https://ipapi.co/json/", {
      cache: "force-cache" // Cache the result
    });

    if (response.ok) {
      const data = await response.json();
      const city = data.city || "";
      const country = data.country_code || "Default";

      // Get nearby cities based on detected city
      let nearby = nearbyCities[city] || [];

      // If no nearby cities found, add the user's city and some from their country
      if (nearby.length === 0) {
        const countryCities = citiesByCountry[country] || citiesByCountry["Default"];
        nearby = city ? [city, ...countryCities.slice(0, 4)] : countryCities;
      } else {
        // Include the user's actual city in the mix
        nearby = [city, ...nearby];
      }

      return { city, country, nearbyCities: nearby };
    }
  } catch {
    // Silently fail and use defaults
  }

  return { city: "", country: "Default", nearbyCities: citiesByCountry["Default"] };
}

export function SocialProofToast() {
  const [notification, setNotification] = useState<PurchaseNotification | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [notificationCount, setNotificationCount] = useState(0);
  const [userLocation, setUserLocation] = useState<UserLocation>({
    city: "",
    country: "Default",
    nearbyCities: citiesByCountry["Default"]
  });
  const [locationLoaded, setLocationLoaded] = useState(false);

  useEffect(() => {
    // Fetch user location via IP on mount
    fetchUserLocation().then((location) => {
      setUserLocation(location);
      setLocationLoaded(true);
    });
  }, []);

  useEffect(() => {
    // Wait for location to be loaded before showing notifications
    if (!locationLoaded) return;

    let timeoutId: NodeJS.Timeout;
    let count = notificationCount;

    const showNotification = () => {
      // Generate new notification
      const newNotification = generateNotification(count, userLocation);
      setNotification(newNotification);
      setIsVisible(true);
      count++;
      setNotificationCount(count);

      // Hide after 4.5 seconds
      setTimeout(() => {
        setIsVisible(false);
      }, 4500);
    };

    const scheduleNext = (isFirst: boolean) => {
      // First notification: 15-30 seconds
      // Subsequent: 35-70 seconds (more spaced out, feels natural)
      const minDelay = isFirst ? 15000 : 35000;
      const maxDelay = isFirst ? 30000 : 70000;
      const delay = minDelay + Math.random() * (maxDelay - minDelay);

      timeoutId = setTimeout(() => {
        showNotification();
        scheduleNext(false);
      }, delay);
    };

    // Start the cycle
    scheduleNext(true);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [locationLoaded, userLocation]);

  return (
    <AnimatePresence>
      {isVisible && notification && (
        <motion.div
          initial={{ opacity: 0, x: -100, y: 20 }}
          animate={{ opacity: 1, x: 0, y: 0 }}
          exit={{ opacity: 0, x: -100 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed bottom-4 left-4 z-50 max-w-sm"
        >
          <div className="bg-card border border-border/50 rounded-xl shadow-lg p-4 backdrop-blur-sm">
            <div className="flex items-start gap-3">
              {/* Success icon */}
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground">
                  {notification.name} from {notification.location}
                </p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  just subscribed to{" "}
                  <span className={`font-semibold ${notification.plan.color}`}>
                    {notification.plan.name}
                  </span>
                </p>
                <div className="flex items-center gap-1 mt-1.5 text-xs text-muted-foreground">
                  <MapPin className="w-3 h-3" />
                  <span>{notification.timeAgo}</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

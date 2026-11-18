# BitLut Privacy Policy

BitLut is an open-source Android application that transfers health and fitness data from Huawei Health to Android Health Connect.

## Data processed

BitLut may read the following data from Huawei Health Kit after user authorization:

- Steps
- Distance
- Activity data
- Activity records
- Recent historical activity data

BitLut may write available records to Android Health Connect.

## No server storage

BitLut does not upload health data to BitLut servers.
BitLut does not operate a backend server.
BitLut does not sell user data.

## Derived workout calorie estimate

BitLut does not create mock steps, distance, workout sessions, elevation, or placeholder health records. If Huawei Health does not provide calories for a real workout, BitLut may calculate an estimated total calorie value from the real workout type and duration for its own app display only. This estimate is local, bounded to the real workout, is not written to Android Health Connect, and is never used to invent another health metric.

## Nutrition journal

The Nutrition tab contains an offline reference catalog of 200 common foods and dishes. You can search it, enter portion weights, calculate calories and protein/fat/carbohydrates, add custom foods, edit your log and set an optional daily calorie target. Searches and calculations stay on the device. These entries are stored only in BitLut's private storage on your device. BitLut does not upload them, does not write them to Android Health Connect, does not read them from Huawei Health, and does not include them in Android app backups. They are removed when you delete them in the app, clear BitLut's app data or uninstall BitLut.

## Optional background access

On supported Health Connect versions BitLut may ask for permission to read already-authorized activity data in the background to refresh its dashboard. Denying it does not prevent Huawei data export. The shared-workout check reads a bounded set of BitLut-written exercise records locally; it cannot inspect another app or confirm corporate import.

## Local processing

Health data is processed locally on the user's Android device and transferred between Huawei Health Kit and Android Health Connect using the permissions granted by the user.

## User control

The user controls permissions through:

- Huawei Health / HMS Core authorization screens
- Android Health Connect permission screens
- Android app settings

The user can revoke permissions at any time.

## Contact

For support or privacy questions, contact the project maintainer through the public GitHub repository.

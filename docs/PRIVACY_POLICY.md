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

BitLut does not create mock steps, distance, workout sessions, elevation, or placeholder health records. If Huawei Health does not provide calories for a real workout, BitLut may calculate an estimated total calorie value from the real workout type/duration and local profile inputs and write it to Health Connect as `TotalCaloriesBurnedRecord`. This estimate is local, bounded to the real workout, and is never used to invent another health metric.

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
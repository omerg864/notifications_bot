# Telegram Notifications Bot

This is a Telegram bot built with Python and Selenium that notifies the active user about coupons 100% off for Udemy courses, notifies the user when it has data about upcoming fuel cost changes, and allows users to request a notification for a movie when it is available for download from YTS.mx. Additionally, the bot has manager commands that can only be accessed with a password.

## Environment Variables

The following environment variables are required to run the bot:

-   `COUPONS_URL`: the URL of the Udemy 100% off coupons page
-   `GOOGLE_CHROME_BIN`: the path to the Google Chrome binary
-   `MISHMAR_RAMLA_ADMIN`: the username for Mishmar Ramla access
-   `MISHMAR_RAMLA_ADMIN_PASS`: the password for Mishmar Ramla access
-   `MONGODB_ACCESS`: the MongoDB access URL
-   `NOTIFICATIONS_BOT_TOKEN`: the Telegram bot token
-   `PORT`: the port for the server to listen on

## Usage

The following commands are available to use with the bot:

-   `/start`: start the bot and display the welcome message
-   `/help`: display the list of available commands
-   `/moviealert`: request a notification for a movie when it is available for download from YTS.mx
-   `/clearmoviealerts`: clear all the movie alerts for the active user
-   `/stopbot`: stop the bot
-   `/deletealert`: delete a movie alert by its ID
-   `/moviealertlist`: display the list of all active movie alerts for the active user
-   `/coupons`: register to 100% off Udemy courses notifications
-   `/unregistercoupons`: unregister from 100% off Udemy courses notifications
-   `/commandlist`: display the list of available commands
-   `/fuelcosts`: display data about upcoming fuel cost changes
-   `/unregisterfuelnotifications`: unregister from fuel cost change notifications
-   `/alertlist`: display the list of all active alerts for the active user
-   `/waitcoupons`: hold the coupons notifications
-   `/exitwaitcoupons`: send all the coupons that were meant to be sent while in hold mode
-   `/chatid`: display the chat ID of the active user
-   `/managercommands`: display the list of available manager commands

The bot also has manager commands that can only be accessed with a password:

-   `/createorg`: creates a new schedule in Mishmar Ramla
-   `/echo`: sends a message to all active chats
-   `/getregistered`: display the list of all registered users
-   `/changepass`: change the password for the manager commands

## Conclusion

The Telegram Notifications Bot is a powerful tool for staying up-to-date on coupons 100% off for Udemy courses, fuel cost changes, and movie availability on YTS.mx. Additionally, it provides manager commands that can be used to create new schedules in Mishmar Ramla, send messages to all active chats, display the list of registered users, and change the password for the manager commands.

## Contributing

Contributions to this project are welcome! To contribute, please fork the repository and create a pull request with your changes. Before submitting a pull request, please make sure that your changes are consistent with the existing code and follow the project's coding standards.

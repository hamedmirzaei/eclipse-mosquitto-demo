// A minimal settings.js to persist flows and installed nodes.
// Node-RED's default settings.js is much larger, this just overrides key parts.

module.exports = {
    // the tcp port that the Node-RED web server is listening on
    uiPort: process.env.PORT || 1880,

    // By default, the Node-RED admin UI is accessible from any IP address.
    // If you need to restrict access, uncomment and configure the `bind` property.
    // bind: '127.0.0.1',

    // The file containing the flows. If not set, it defaults to flows_<hostname>.json
    // If you set this, you should also ensure your container restarts with --name.
    // flowsFile: 'flows.json',

    // The `userDir` property is the directory used to store users' flows,
    // credentials, and node modules. By default, this is the .node-red
    // directory in the user's home directory.
    // This is crucial for persistence inside Docker.
    userDir: '/data',

    // Configure the logging output
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },

    // To disable the editor and run just the flows, set this to false
    // disableEditor: false,

    // To enable the Projects feature, set this to true
    // projects: {
    //     enabled: true
    // },

    // To enable the library of example flows, uncomment the following line
    // flowFilePretty: true,

    // To set a code editor theme for the editor, uncomment the following line
    // editorTheme: "ace/theme/tomorrow_night_eighties",

    // To enable or disable the Node-RED Dashboard (requires node-red-dashboard to be installed)
    // ui: {
    //     path: "ui" // The path the UI will be served from, eg: http://localhost:1880/ui
    // },

    // To enable authentication for the editor (and optionally the UI)
    // adminAuth: {
    //     type: "credentials",
    //     users: [{
    //         username: "admin",
    //         password: "$2a$08$zC.8w/Q/q.f6Z/z8R8J8UuY.Bw.T.Q.z.2.y.H.x.H.Q.u.B.w.z.2.", // bcrypt hash of "password"
    //         permissions: "*"
    //     }]
    // }
};
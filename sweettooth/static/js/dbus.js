"use strict";

// We need to abuse the plugin system so that we can defer the
// load completion until our dynamically built requirement is
// loaded.

// Thanks to James Burke for helping me with this.
// http://groups.google.com/group/requirejs/msg/cc6016210c53a51d

define({
    load: function(name, req, onLoad, config) {
        req(['jquery'], function ($) {
            if (!('SweetTooth' in window)) {
                try {
                    var MIME_TYPE = 'application/x-gnome-shell-integration';
                    var $plg = $('<embed>', { type: MIME_TYPE });

                    // Netscape plugins are strange: if you make them invisible with
                    // CSS or give them 0 width/height, they won't load. Just smack it
                    // off-screen so it isn't visible, but still works.
                    $plg.css({ position: 'absolute',
                               left: '-1000em',
                               top: '-1000em' });

                    // TODO: this may not work if the DOM is not ready
                    // when this call is made. Depending on browsers
                    // you want to support, either listen to
                    // DOMContentLoaded, event, or use $(function(){}), but in
                    // those cases, the full body of this load action should
                    // be in that call.
                    $(document.body).append($plg);

                    // The API is defined on the plugin itself.
                    window.SweetTooth = $plg[0];
                } catch (e) {
                    // In this case we probably failed the origin checks and
                    // the NPAPI plugin spat out an error. Explicitly set the
                    // plugin to NULL
                    window.SweetTooth = null;
                }
            }

            if (name == "API") {
                onLoad(window.SweetTooth);
                return;
            }

            var apiVersion = undefined;

            try {
                if (window.SweetTooth) {
                    apiVersion = window.SweetTooth.apiVersion;
                }
            } catch (e) { }

            if (!apiVersion)
                apiVersion = 'dummy';

            var scriptname = './versions/' + apiVersion + '/main';
            // requirejs caches response.
            req([scriptname], function(module) {
                onLoad(module);
            });
        });
    }
});

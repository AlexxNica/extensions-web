
"use strict";

define({
  "extensions/comment": "<div class=\"comment\">\n  {{#is_extension_creator}}\n  <div class=\"extension-creator-badge\">Author</div>\n  {{/is_extension_creator}}\n  <img src=\"{{gravatar}}\" class=\"gravatar\">\n  <div class=\"rating-author\">\n    {{#rating}}\n      <div class=\"rating\" data-rating-value=\"{{rating}}\"></div> by\n    {{/rating}}\n    <a class=\"comment-author\" href=\"{{author.url}}\">{{author.username}}</a>\n    <p>{{comment}}</p>\n    <time datetime=\"{{date.timestamp}}Z\">{{date.standard}}</time>\n  </div>\n</div>",
  "extensions/comments_list": "{{#comments}}\n  {{>extensions/comment}}\n  <hr>\n{{/comments}}\n{{^show_all}}\n<p class=\"show-all\">Show more reviews</p>\n{{/show_all}}\n\n{{^comments}}\n  <p>There are no comments. Be the first!</p>\n{{/comments}}",
  "extensions/error_report_template": "What's wrong?\n\n\n\nWhat have you tried?\n\n\n\nAutomatically detected errors:\n\n{{#errors}}\n  {{.}}\n\n================\n{{/errors}}\n{{^errors}}\nGNOME Shell Extensions did not detect any errors with this extension.\n{{/errors}}\n\nVersion information:\n\n    Shell version: {{sv}}\n    Extension version: {{#ev}}{{ev}}{{/ev}}{{^ev}}Unknown{{/ev}}",
  "extensions/info": "<div class=\"extension\" data-uuid=\"{{uuid}}\">\n  {{>extensions/info_contents}}\n</div>",
  "extensions/info_contents": "<div class=\"switch\"></div>\n<div class=\"extra-buttons\">\n  <div class=\"upgrade-button\" title=\"Upgrade this extension\"></div>\n  <div class=\"configure-button\" title=\"Configure this extension\"></div>\n</div>\n<h3 class=\"extension-name\">\n  {{#link}}\n    <a href=\"{{link}}\" class=\"title-link\"> <img src=\"{{icon}}\" class=\"icon\"> {{name}} </a>\n  {{/link}}\n  {{^link}}\n  {{name}}\n  {{/link}}\n</h3>\n{{#creator}}\n  <span class=\"author\">by <a href=\"{{creator_url}}\"> {{creator}} </a></span>\n{{/creator}}\n<p class=\"description\">{{first_line_of_description}}</p>\n{{#want_uninstall}}\n  <button class=\"uninstall\" title=\"Uninstall\">Uninstall</button>\n{{/want_uninstall}}",
  "extensions/info_list": "<ul class=\"extensions\">\n{{#extensions}}\n  <li class=\"extension\" data-svm=\"{{shell_version_map}}\">\n    {{>extensions/info_contents}}\n  </li>\n{{/extensions}}\n</ul>",
  "extensions/uninstall": "You uninstalled <b>{{name}}</b>.",
  "messages/cannot_list_errors": "GNOME Shell Extensions cannot automatically detect any errors.",
  "messages/cannot_list_local": "GNOME Shell Extensions cannot list your installed extensions.",
  "messages/dummy_proxy": "You do not appear to have an up to date version of GNOME3. You won't be able to install extensions from here. See the <a href=\"/about/#old-version\">about page</a> for more information."
});

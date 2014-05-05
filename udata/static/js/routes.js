/**
 * Configure the router
 */
define(['jquery', 'router', 'logger'], function($, router, log) {

    var lang = $('html').attr('lang');

    function i18n(path) {
        return '/' + lang + path;
    }

    router.registerRoutes({
        home: {path: i18n('/'), moduleId: 'home'},
        metrics: {path: i18n('/metrics/'), moduleId: 'dashboard/site'},

        // Datasets routes
        datasetSearch: {path: i18n('/datasets/'), moduleId: 'search'},
        datasetNew: {path: i18n('/datasets/new/'), moduleId: 'dataset/form'},
        datasetDisplay: {path: i18n('/datasets/:slug_or_id/'), moduleId: 'dataset/display'},
        datasetEdit: {path: i18n('/datasets/:slug_or_id/edit/'), moduleId: 'dataset/form'},

        // Resources routes
        resourceNew: {path: i18n('/datasets/:slug_or_id/resources/new/'), moduleId: 'dataset/resource-form'},
        resourceEdit: {path: i18n('/datasets/:slug_or_id/resources/:rid/edit/'), moduleId: 'dataset/resource-form'},

        // Organizations routes
        orgSearch: {path: i18n('/organizations/'), moduleId: 'search'},
        orgNew: {path: i18n('/organizations/new/'), moduleId: 'organization/form'},
        orgDisplay: {path: i18n('/organizations/:slug_or_id/'), moduleId: 'organization/display'},
        orgEdit: {path: i18n('/organizations/:slug_or_id/edit/'), moduleId: 'organization/form'},
        orgMembers: {path: i18n('/organizations/:slug_or_id/edit/members/'), moduleId: 'organization/members'},

        // Reuses routes
        reuseSearch: {path: i18n('/reuses/'), moduleId: 'search'},
        reuseNew: {path: i18n('/reuses/new/'), moduleId: 'reuse/form'},
        reuseDisplay: {path: i18n('/reuses/:slug_or_id/'), moduleId: 'reuse/display'},
        reuseEdit: {path: i18n('/reuses/:slug_or_id/edit/'), moduleId: 'reuse/form'},

        // Topics routes
        topicDisplay: {path: i18n('/topics/:slug_or_id/'), moduleId: 'topic/display'}
    })
    .on('routeload', function(module, routeArguments) {
        log.debug('Module "'+router.activeRoute.moduleId+'" loaded by route "'+router.activeRoute.path+'"');
        if (module && module.hasOwnProperty('start')) {
            log.debug('Starting module "'+router.activeRoute.moduleId+'" with parameters:', routeArguments);
            module.start();
        }
    });

    return {
        start: function() {
            log.debug('Router starting');
            // Set up event handlers and trigger the initial page load
            router.init({
                // fireInitialStateChange: false
            });
            log.debug('Router starting');
        }
    }
});

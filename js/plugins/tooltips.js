import log from 'logger';
import tooltip from 'components/tooltip.vue';
import popover from 'components/popover.vue';


export function install(Vue) {
    /**
     * Attach a tooltip on the element.
     */
    Vue.directive('tooltip', {
        params: ['title', 'tooltipPlacement', 'tooltipEffect'],
        /**
         * Insert the tooltip element and attach the event listeners
         */
        bind() {
            this.tooltipEl = document.createElement('span');
            document.body.appendChild(this.tooltipEl);

            this.tooltip = new Vue(Object.assign({
                el: this.tooltipEl,
                parent: this.vm,
                propsData: {
                    target: this.el,
                    content: this.params.title,
                    placement: this.params.tooltipPlacement || 'top',
                    effect: this.params.tooltipEffect || 'fadein',
                }
            }, tooltip));

            this._mouseenterHandler = this.el.addEventListener('mouseenter', this.showTooltip.bind(this));
            this._mouseleaveHandler = this.el.addEventListener('mouseleave', this.hideTooltip.bind(this));
            this._focusHandler = this.el.addEventListener('focus', this.showTooltip.bind(this));
            this._blurHandler = this.el.addEventListener('blur', this.hideTooltip.bind(this));

            // Easy tooltip setting
            this.el.setTooltip = function(content, show) {
                this.tooltip.content = content;
                if (show) this.showTooltip();
            }.bind(this);
        },
        /**
         * Update the tooltip content
         */
        update(value) {
            if (value) this.tooltip.content = value;
        },
        /**
         * Remove event listeners
         */
        unbind() {
            this.el.removeEventListener('blur', this._blurHandler);
            this.el.removeEventListener('focus', this._focusHandler);
            this.el.removeEventListener('mouseenter', this._mouseenterHandler);
            this.el.removeEventListener('mouseleave', this._mouseleaveHandler);
        },
        showTooltip() {
            this.tooltip.show = true;
        },
        hideTooltip() {
            this.tooltip.show = false;
        },
        paramWatchers: {
            title(value) {
                if (this.arg) return; // Only set if no explicit content is provided
                this.tooltip.content = value;
            }
        }
    });

    /**
     * Attach a popover on the element.
     */
    Vue.directive('popover', {
        params: ['title', 'popoverTitle', 'popoverPlacement', 'popoverTrigger', 'popoverEffect', 'popoverLarge'],
        /**
         * Insert the popover element and attach the event listeners
         */
        bind() {
            this.popoverEl = document.createElement('span');
            document.body.appendChild(this.popoverEl);

            this.trigger = this.params.popoverTrigger || 'click';

            this.popover = new Vue(Object.assign({
                el: this.popoverEl,
                parent: this.vm,
                propsData: {
                    target: this.el,
                    title: this.params.popoverTitle || this.params.title,
                    placement: this.params.popoverPlacement || 'top',
                    effect: this.params.popoverEffect || 'fadein',
                    large: this.params.popoverLarge || false,
                }
            }, popover));

            switch(this.trigger) {
                case 'hover':
                    this._mouseenterHandler = this.el.addEventListener('mouseenter', this.showPopover.bind(this));
                    this._mouseleaveHandler = this.el.addEventListener('mouseleave', this.hidePopover.bind(this));
                    break;
                case 'focus':
                    this._focusHandler = this.el.addEventListener('focus', this.showPopover.bind(this));
                    this._blurHandler = this.el.addEventListener('blur', this.hidePopover.bind(this));
                    break;
                case 'click':
                    this._clickHandler = this.el.addEventListener('click', this.popover.toggle);
                    break;
                default:
                    return log.error(`Unsupported trigger '${this.trigger}'`);
            }
        },
        /**
         * Update the popover content
         */
        update(value) {
            if (value) this.popover.content = value;
        },
        /**
         * Remove event listeners
         */
        unbind() {
            this.el.removeEventListener('blur', this._blurHandler);
            this.el.removeEventListener('focus', this._focusHandler);
            this.el.removeEventListener('mouseenter', this._mouseenterHandler);
            this.el.removeEventListener('mouseleave', this._mouseleaveHandler);
            this.el.removeEventListener('clic', this._clickHandler);
        },
        showPopover() {
            this.popover.show = true;
        },
        hidePopover() {
            this.popover.show = false;
        },
        paramWatchers: {
            title(value) {
                if (!this.params.popoverTitle) {
                    this.popover.title = value;
                }
            },
            popoverTitle(value) {
                this.popover.title = value;
            },
        }
    });

    /**
     * Attach a popover on the element.
     */
    Vue.directive('popover-content', {
        /**
         * Transclude the popover content into the popover
         */
        bind() {
            const popover = this.findPopover();
            if (!popover) {
                log.error('popover-content need a parent popover directive');
                return;
            }
            popover.content = this.el;
        },
        /**
         * Find the closest parent node with a popover directive.
         * @return {Vue} The target popover component
         */
        findPopover() {
            let el = this.el;
            while (el.parentElement) {
                el = el.parentElement;
                if (el._vue_directives) {
                    for (const directive of el._vue_directives) {
                        if (directive.name === 'popover') return directive.popover;
                    }
                }
            }
        }
    });
}

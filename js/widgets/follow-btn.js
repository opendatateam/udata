/*
 * Follow button
 */
import $ from 'jquery';
import Auth from 'auth';
import i18n from 'i18n';

const DEFAULTS = {
    follow_icon: 'glyphicon glyphicon-eye-open',
    following_icon: 'glyphicon glyphicon-eye-close',
    follow_label: i18n._('Follow'),
    following_label: i18n._('Following')
};

// Handle featured button
$('.btn-follow').click(function(e) {
    e.preventDefault()
    const $this = $(this);
    const $icon = $this.find('.glyphicon,.fa');
    const follow_icon = $this.data('follow-icon') || DEFAULTS.follow_icon;
    const following_icon = $this.data('following-icon') || DEFAULTS.following_icon;
    const has_text = $.trim($this.text()).length > 0;

    if (!Auth.need_user(i18n._('You need to be logged in to follow.'))) {
        return false;
    }

    if ($this.hasClass('active')) {
        $.ajax({
            url: $this.data('api-url'),
            type: 'DELETE',
            success: function() {
                const label = $this.data('follow-label') || DEFAULTS.follow_label;

                $icon.removeClass(following_icon).addClass(follow_icon);
                $this.removeClass('active')
                    .attr('title', label).attr('data-original-title', label)
                    .tooltip('fixTitle');

                if (has_text) {
                    $this.text(label).prepend($icon);
                }
            }
        });
    } else {
        $.post($this.data('api-url'), function() {
            const label = $this.data('following-label') || DEFAULTS.following_label;

            $icon.removeClass(follow_icon).addClass(following_icon);
            $this.addClass('active')
                .attr('title', label).attr('data-original-title', label)
                .tooltip('fixTitle');

            if (has_text) {
                $this.text(label).prepend($icon);
            }
        });
    }

    return false;
});

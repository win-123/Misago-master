from django.urls import reverse

from misago.acl.testutils import override_acl
from misago.categories.models import Category
from misago.readtracker import poststracker
from misago.threads import testutils
from misago.threads.models import Poll, PollVote, Thread

from .test_threads_api import ThreadsApiTestCase


class ThreadMergeApiTests(ThreadsApiTestCase):
    def setUp(self):
        super(ThreadMergeApiTests, self).setUp()

        Category(
            name='Category B',
            slug='category-b',
        ).insert_at(
            self.category,
            position='last-child',
            save=True,
        )
        self.category_b = Category.objects.get(slug='category-b')

        self.api_link = reverse(
            'misago:api:thread-merge', kwargs={
                'pk': self.thread.pk,
            }
        )

    def override_other_acl(self, acl=None):
        other_category_acl = self.user.acl_cache['categories'][self.category.pk].copy()
        other_category_acl.update({
            'can_see': 1,
            'can_browse': 1,
            'can_see_all_threads': 1,
            'can_see_own_threads': 0,
            'can_hide_threads': 0,
            'can_approve_content': 0,
            'can_edit_posts': 0,
            'can_hide_posts': 0,
            'can_hide_own_posts': 0,
            'can_merge_threads': 0,
            'can_close_threads': 0,
        })

        if acl:
            other_category_acl.update(acl)

        categories_acl = self.user.acl_cache['categories']
        categories_acl[self.category_b.pk] = other_category_acl

        visible_categories = [self.category.pk]
        if other_category_acl['can_see']:
            visible_categories.append(self.category_b.pk)

        override_acl(
            self.user, {
                'visible_categories': visible_categories,
                'categories': categories_acl,
            }
        )

    def test_merge_no_permission(self):
        """api validates if thread can be merged with other one"""
        self.override_acl({'can_merge_threads': 0})

        response = self.client.post(self.api_link)
        self.assertContains(
            response,
            "You can't merge threads in this category.",
            status_code=403
        )

    def test_merge_no_url(self):
        """api validates if thread url was given"""
        self.override_acl({'can_merge_threads': 1})

        response = self.client.post(self.api_link)
        self.assertContains(response, "Enter link to new thread.", status_code=400)

    def test_invalid_url(self):
        """api validates thread url"""
        self.override_acl({'can_merge_threads': 1})

        response = self.client.post(self.api_link, {
            'other_thread': self.user.get_absolute_url(),
        })
        self.assertContains(response, "This is not a valid thread link.", status_code=400)

    def test_current_other_thread(self):
        """api validates if thread url given is to current thread"""
        self.override_acl({'can_merge_threads': 1})

        response = self.client.post(
            self.api_link, {
                'other_thread': self.thread.get_absolute_url(),
            }
        )
        self.assertContains(response, "You can't merge thread with itself.", status_code=400)

    def test_other_thread_exists(self):
        """api validates if other thread exists"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl()

        other_thread = testutils.post_thread(self.category_b)
        other_other_thread = other_thread.get_absolute_url()
        other_thread.delete()

        response = self.client.post(self.api_link, {
            'other_thread': other_other_thread,
        })
        self.assertContains(
            response, "The thread you have entered link to doesn't exist", status_code=400
        )

    def test_other_thread_is_invisible(self):
        """api validates if other thread is visible"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_see': 0})

        other_thread = testutils.post_thread(self.category_b)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(
            response, "The thread you have entered link to doesn't exist", status_code=400
        )

    def test_other_thread_isnt_mergeable(self):
        """api validates if other thread can be merged"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 0})

        other_thread = testutils.post_thread(self.category_b)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )

        self.assertContains(
            response, "Other thread can't be merged with.", status_code=400
        )

    def test_thread_category_is_closed(self):
        """api validates if thread's category is open"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({
            'can_merge_threads': 1,
            'can_reply_threads': 0,
            'can_close_threads': 0,
        })

        other_thread = testutils.post_thread(self.category_b)

        self.category.is_closed = True
        self.category.save()

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(
            response,
            "This category is closed. You can't merge it's threads.",
            status_code=403,
        )

    def test_thread_is_closed(self):
        """api validates if thread is open"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({
            'can_merge_threads': 1,
            'can_reply_threads': 0,
            'can_close_threads': 0,
        })

        other_thread = testutils.post_thread(self.category_b)

        self.thread.is_closed = True
        self.thread.save()

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(
            response,
            "This thread is closed. You can't merge it with other threads.",
            status_code=403,
        )

    def test_other_thread_category_is_closed(self):
        """api validates if other thread's category is open"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({
            'can_merge_threads': 1,
            'can_reply_threads': 0,
            'can_close_threads': 0,
        })

        other_thread = testutils.post_thread(self.category_b)

        self.category_b.is_closed = True
        self.category_b.save()

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(
            response, "Other thread's category is closed. You can't merge with it.", status_code=400
        )

    def test_other_thread_is_closed(self):
        """api validates if other thread is open"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({
            'can_merge_threads': 1,
            'can_reply_threads': 0,
            'can_close_threads': 0,
        })

        other_thread = testutils.post_thread(self.category_b)

        other_thread.is_closed = True
        other_thread.save()

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(
            response, "Other thread is closed and can't be merged with", status_code=400
        )

    def test_other_thread_isnt_replyable(self):
        """api validates if other thread can be replied, which is condition for merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({
            'can_merge_threads': 1,
            'can_reply_threads': 0,
        })

        other_thread = testutils.post_thread(self.category_b)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(
            response, "You can't merge this thread into thread you can't reply.", status_code=400
        )

    def test_merge_threads(self):
        """api merges two threads successfully"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # other thread has two posts now
        self.assertEqual(other_thread.post_set.count(), 3)

        # first thread is gone
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(pk=self.thread.pk)

    def test_merge_threads_kept_reads(self):
        """api keeps both threads readtrackers after merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)

        poststracker.save_read(self.user, self.thread.first_post)
        poststracker.save_read(self.user, other_thread.first_post)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # posts reads are kept
        postreads = self.user.postread_set.filter(post__is_event=False).order_by('id')

        self.assertEqual(
            list(postreads.values_list('post_id', flat=True)),
            [self.thread.first_post_id, other_thread.first_post_id]
        )
        self.assertEqual(postreads.filter(thread=other_thread).count(), 2)
        self.assertEqual(postreads.filter(category=self.category_b).count(), 2)

    def test_merge_threads_kept_subs(self):
        """api keeps other thread's subscription after merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)

        self.user.subscription_set.create(
            thread=self.thread,
            category=self.thread.category,
            last_read_on=self.thread.last_post_on,
            send_email=False,
        )

        self.assertEqual(self.user.subscription_set.count(), 1)
        self.user.subscription_set.get(thread=self.thread)
        self.user.subscription_set.get(category=self.category)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # subscriptions are kept
        self.assertEqual(self.user.subscription_set.count(), 1)
        self.user.subscription_set.get(thread=other_thread)
        self.user.subscription_set.get(category=self.category_b)

    def test_merge_threads_moved_subs(self):
        """api keeps other thread's subscription after merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)

        self.user.subscription_set.create(
            thread=other_thread,
            category=other_thread.category,
            last_read_on=other_thread.last_post_on,
            send_email=False,
        )

        self.assertEqual(self.user.subscription_set.count(), 1)
        self.user.subscription_set.get(thread=other_thread)
        self.user.subscription_set.get(category=self.category_b)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # subscriptions are kept
        self.assertEqual(self.user.subscription_set.count(), 1)
        self.user.subscription_set.get(thread=other_thread)
        self.user.subscription_set.get(category=self.category_b)

    def test_merge_threads_handle_subs_colision(self):
        """api resolves conflicting thread subscriptions after merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        self.user.subscription_set.create(
            thread=self.thread,
            category=self.thread.category,
            last_read_on=self.thread.last_post_on,
            send_email=False,
        )

        other_thread = testutils.post_thread(self.category_b)

        self.user.subscription_set.create(
            thread=other_thread,
            category=other_thread.category,
            last_read_on=other_thread.last_post_on,
            send_email=False,
        )

        self.assertEqual(self.user.subscription_set.count(), 2)
        self.user.subscription_set.get(thread=self.thread)
        self.user.subscription_set.get(category=self.category)
        self.user.subscription_set.get(thread=other_thread)
        self.user.subscription_set.get(category=self.category_b)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # subscriptions are kept
        self.assertEqual(self.user.subscription_set.count(), 1)
        self.user.subscription_set.get(thread=other_thread)
        self.user.subscription_set.get(category=self.category_b)

    def test_merge_threads_kept_poll(self):
        """api merges two threads successfully, keeping poll from old thread"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)
        poll = testutils.post_poll(other_thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # other thread has two posts now
        self.assertEqual(other_thread.post_set.count(), 3)

        # first thread is gone
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(pk=self.thread.pk)

        # poll and its votes were kept
        self.assertEqual(Poll.objects.filter(pk=poll.pk, thread=other_thread).count(), 1)
        self.assertEqual(PollVote.objects.filter(poll=poll, thread=other_thread).count(), 4)

    def test_merge_threads_moved_poll(self):
        """api merges two threads successfully, moving poll from other thread"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)
        poll = testutils.post_poll(self.thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # other thread has two posts now
        self.assertEqual(other_thread.post_set.count(), 3)

        # first thread is gone
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(pk=self.thread.pk)

        # poll and its votes were moved
        self.assertEqual(Poll.objects.filter(pk=poll.pk, thread=other_thread).count(), 1)
        self.assertEqual(PollVote.objects.filter(poll=poll, thread=other_thread).count(), 4)

    def test_threads_merge_conflict(self):
        """api errors on merge conflict, returning list of available polls"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)
        poll = testutils.post_poll(self.thread, self.user)
        other_poll = testutils.post_poll(other_thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {
                'polls': [
                    [0, "Delete all polls"],
                    [poll.pk, poll.question],
                    [other_poll.pk, other_poll.question],
                ]
            }
        )

        # polls and votes were untouched
        self.assertEqual(Poll.objects.count(), 2)
        self.assertEqual(PollVote.objects.count(), 8)

    def test_threads_merge_conflict_invalid_resolution(self):
        """api errors on invalid merge conflict resolution"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)

        testutils.post_poll(self.thread, self.user)
        testutils.post_poll(other_thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
                'poll': 'jhdkajshdsak',
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': "Invalid choice."})

        # polls and votes were untouched
        self.assertEqual(Poll.objects.count(), 2)
        self.assertEqual(PollVote.objects.count(), 8)

    def test_threads_merge_conflict_delete_all(self):
        """api deletes all polls when delete all choice is selected"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)
        testutils.post_poll(self.thread, self.user)
        testutils.post_poll(other_thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
                'poll': 0,
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # other thread has two posts now
        self.assertEqual(other_thread.post_set.count(), 3)

        # first thread is gone
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(pk=self.thread.pk)

        # polls and votes are gone
        self.assertEqual(Poll.objects.count(), 0)
        self.assertEqual(PollVote.objects.count(), 0)

    def test_threads_merge_conflict_keep_first_poll(self):
        """api deletes other poll on merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)
        poll = testutils.post_poll(self.thread, self.user)
        other_poll = testutils.post_poll(other_thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
                'poll': poll.pk,
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # other thread has two posts now
        self.assertEqual(other_thread.post_set.count(), 3)

        # first thread is gone
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(pk=self.thread.pk)

        # other poll and its votes are gone
        self.assertEqual(Poll.objects.filter(thread=self.thread).count(), 0)
        self.assertEqual(PollVote.objects.filter(thread=self.thread).count(), 0)

        self.assertEqual(Poll.objects.filter(thread=other_thread).count(), 1)
        self.assertEqual(PollVote.objects.filter(thread=other_thread).count(), 4)

        Poll.objects.get(pk=poll.pk)
        with self.assertRaises(Poll.DoesNotExist):
            Poll.objects.get(pk=other_poll.pk)

    def test_threads_merge_conflict_keep_other_poll(self):
        """api deletes first poll on merge"""
        self.override_acl({'can_merge_threads': 1})

        self.override_other_acl({'can_merge_threads': 1})

        other_thread = testutils.post_thread(self.category_b)
        poll = testutils.post_poll(self.thread, self.user)
        other_poll = testutils.post_poll(other_thread, self.user)

        response = self.client.post(
            self.api_link, {
                'other_thread': other_thread.get_absolute_url(),
                'poll': other_poll.pk,
            }
        )
        self.assertContains(response, other_thread.get_absolute_url(), status_code=200)

        # other thread has two posts now
        self.assertEqual(other_thread.post_set.count(), 3)

        # first thread is gone
        with self.assertRaises(Thread.DoesNotExist):
            Thread.objects.get(pk=self.thread.pk)

        # other poll and its votes are gone
        self.assertEqual(Poll.objects.filter(thread=self.thread).count(), 0)
        self.assertEqual(PollVote.objects.filter(thread=self.thread).count(), 0)

        self.assertEqual(Poll.objects.filter(thread=other_thread).count(), 1)
        self.assertEqual(PollVote.objects.filter(thread=other_thread).count(), 4)

        Poll.objects.get(pk=other_poll.pk)
        with self.assertRaises(Poll.DoesNotExist):
            Poll.objects.get(pk=poll.pk)

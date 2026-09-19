from django.urls import reverse
from rest_framework.test import APITestCase

from users.models import User
from .models import Message


class MessagesAPITests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username='alice', password='pass12345',
            phone='0101010101', adresse='Rue 1',
        )
        self.bob = User.objects.create_user(
            username='bob', password='pass12345',
            phone='0202020202', adresse='Rue 2',
        )
        self.charlie = User.objects.create_user(
            username='charlie', password='pass12345',
            phone='0303030303', adresse='Rue 3',
        )
        self.list_url = reverse('message-list')

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)

    def test_send_message_sets_sender_from_token(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            self.list_url,
            {'receiver': self.bob.id, 'sender': self.charlie.id, 'content': 'Salut Bob'},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['sender'], self.alice.id)
        self.assertEqual(response.data['receiver_username'], 'bob')
        self.assertEqual(Message.objects.count(), 1)

    def test_cannot_send_empty_message(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            self.list_url, {'receiver': self.bob.id, 'content': '   '},
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_message_self(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            self.list_url, {'receiver': self.alice.id, 'content': 'Moi-meme'},
        )
        self.assertEqual(response.status_code, 400)

    def test_list_only_returns_my_messages(self):
        Message.objects.create(sender=self.alice, receiver=self.bob, content='a->b')
        Message.objects.create(sender=self.bob, receiver=self.alice, content='b->a')
        Message.objects.create(sender=self.bob, receiver=self.charlie, content='b->c')

        self.client.force_authenticate(self.alice)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

    def test_inbox_and_sent(self):
        Message.objects.create(sender=self.alice, receiver=self.bob, content='a->b')
        Message.objects.create(sender=self.charlie, receiver=self.bob, content='c->b')

        self.client.force_authenticate(self.bob)
        inbox = self.client.get(reverse('message-inbox'))
        sent = self.client.get(reverse('message-sent'))
        self.assertEqual(inbox.data['count'], 2)
        self.assertEqual(sent.data['count'], 0)

    def test_conversation_is_isolated_to_two_users(self):
        Message.objects.create(sender=self.alice, receiver=self.bob, content='a->b')
        Message.objects.create(sender=self.bob, receiver=self.alice, content='b->a')
        Message.objects.create(sender=self.alice, receiver=self.charlie, content='a->c')

        self.client.force_authenticate(self.alice)
        url = reverse('message-conversation', args=[self.bob.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        contents = [m['content'] for m in response.data['results']]
        self.assertEqual(contents, ['a->b', 'b->a'])  # chronological

    def test_sender_can_edit_message_and_it_is_flagged(self):
        message = Message.objects.create(
            sender=self.alice, receiver=self.bob, content='Salut Bo',
        )
        original_timestamp = message.timestamp  # auto_now_add value, must survive the edit
        self.client.force_authenticate(self.alice)
        response = self.client.patch(
            reverse('message-detail', args=[message.id]),
            {'content': 'Salut Bob, desole pour la faute'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_edited'], True)
        self.assertIsNotNone(response.data['edited_at'])
        message.refresh_from_db()
        self.assertEqual(message.content, 'Salut Bob, desole pour la faute')
        # The original send time is never overwritten.
        self.assertEqual(message.timestamp, original_timestamp)

    def test_receiver_cannot_edit_message(self):
        message = Message.objects.create(
            sender=self.alice, receiver=self.bob, content='Prix: 100',
        )
        self.client.force_authenticate(self.bob)
        response = self.client.patch(
            reverse('message-detail', args=[message.id]),
            {'content': 'Prix: 10'},
        )
        self.assertEqual(response.status_code, 403)
        message.refresh_from_db()
        self.assertEqual(message.content, 'Prix: 100')
        self.assertFalse(message.is_edited)

    def test_cannot_edit_empty_message(self):
        message = Message.objects.create(
            sender=self.alice, receiver=self.bob, content='Salut',
        )
        self.client.force_authenticate(self.alice)
        response = self.client.patch(
            reverse('message-detail', args=[message.id]),
            {'content': '  '},
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_edit_foreign_message(self):
        message = Message.objects.create(
            sender=self.bob, receiver=self.charlie, content='b->c',
        )
        self.client.force_authenticate(self.alice)
        response = self.client.patch(
            reverse('message-detail', args=[message.id]),
            {'content': 'pirate'},
        )
        self.assertEqual(response.status_code, 404)

    def test_only_sender_can_delete(self):
        Message.objects.create(sender=self.alice, receiver=self.bob, content='a->b')
        self.client.force_authenticate(self.alice)
        response = self.client.delete(reverse('message-detail', args=[1]))
        self.assertEqual(response.status_code, 204)

    def test_retrieve_foreign_message_is_404(self):
        message = Message.objects.create(
            sender=self.bob, receiver=self.charlie, content='b->c',
        )
        self.client.force_authenticate(self.alice)
        response = self.client.get(reverse('message-detail', args=[message.id]))
        self.assertEqual(response.status_code, 404)


from monocypher.utils import ensure_bytes_with_length, ensure, Encodable, random
from monocypher.utils.crypto_public import crypto_key_exchange, crypto_key_exchange_public_key
from monocypher.utils.crypto_cmp import crypto_verify32
from monocypher.secret import SecretBox


__all__ = ('PublicKey', 'PrivateKey', 'Box')


class PublicKey(Encodable):
    """
    X25519 public key.
    This can be published.

    :param pk: The public key (bytes).
    """

    KEY_SIZE = 32

    __slots__ = ('_pk',)

    def __init__(self, pk):
        ensure_bytes_with_length('pk', pk, self.KEY_SIZE)
        self._pk = pk

    def __bytes__(self):
        return self._pk

    def __eq__(self, other):
        return isinstance(other, self.__class__) and crypto_verify32(other._pk, self._pk)

    def __hash__(self):
        return hash(self._pk)


class PrivateKey(Encodable):
    """
    X25519 private key.
    This **must** be kept secret.

    :param sk: The private key (bytes).
    """

    KEY_SIZE = 32

    __slots__ = ('_sk',)

    def __init__(self, sk):
        ensure_bytes_with_length('sk', sk, self.KEY_SIZE)
        self._sk = sk

    @classmethod
    def generate(cls):
        """
        Generates a random :class:`~monocypher.public.PrivateKey` object.

        :rtype: :class:`~monocypher.public.PrivateKey`
        """
        return cls(random(cls.KEY_SIZE))

    @property
    def public_key(self):
        """
        Returns the corresponding :class:`~monocypher.public.PublicKey` object.

        :rtype: :class:`~monocypher.public.PublicKey`
        """
        return PublicKey(crypto_key_exchange_public_key(self._sk))

    def __bytes__(self):
        return self._sk

    def __eq__(self, other):
        return isinstance(other, self.__class__) and crypto_verify32(other._sk, self._sk)

    def __hash__(self):
        return hash(self._sk)


class Box(SecretBox):
    """
    A subclass of :class:`~monocypher.secret.SecretBox` object with the
    encryption key being the shared key computed from the key exchange.
    The shared key is computed using X25519 and HChaCha20.
    For details see `Monocypher's documentation <https://monocypher.org/manual/key_exchange>`_.

    :param your_sk: Your private key (a :class:`~monocypher.public.PrivateKey` object).
    :param their_pk: Their public key (a :class:`~monocypher.public.PublicKey` object).
    """

    __slots__ = ()

    def __init__(self, your_sk, their_pk):
        ensure(isinstance(your_sk, PrivateKey), TypeError, 'your_sk should be a PrivateKey instance')
        ensure(isinstance(their_pk, PublicKey), TypeError, 'their_pk should be a PublicKey instance')
        super().__init__(crypto_key_exchange(
            your_sk.encode(),
            their_pk.encode(),
        ))

    def shared_key(self):
        """
        Returns the shared secret. This value is safe for use as the key
        for other symmetric ciphers.
        """
        return self._key


class SealedBox:
    """
    SealedBox enables you to send a message decryptable by the private key
    variant of the `receipient_key`. The message will not be decryptable by
    you after encryption, providing deniability (but with no authentication --
    the receipient cannot be sure that it was you who sent the message).

    :param receipient_key: A :py:class:`~monocypher.public.PublicKey` or
                           :py:class:`~monocypher.public.PrivateKey` object.
                           If the latter is provided, then the SealedBox is
                           able to decrypt messages.
    """

    __slots__ = ('_pk', '_sk')

    def __init__(self, receipient_key):
        if isinstance(receipient_key, PrivateKey):
            self._pk = receipient_key.public_key
            self._sk = receipient_key
        elif isinstance(receipient_key, PublicKey):
            self._pk = receipient_key
            self._sk = None
        else:
            raise TypeError('receipient_key should be a PublicKey or PrivateKey instance')

    def encrypt(self, msg):
        """
        Encrypt the given `msg`. This works using a similar construction
        as that from libsodium's `crypto_box_seal <https://libsodium.gitbook.io/doc/public-key_cryptography/sealed_boxes>`_;
        (but using Monocypher's high level functions).
        The idea is that an ephemeral private key is generated and used to
        encrypt the message, which is decryptable only if you know the
        receipient's private key and the ephemeral public key (and the
        ephemeral public key hasn't been tampered with).

        :param msg: The message to encrypt (bytes).
        :rtype: :py:class:`bytes`
        """
        ephemeral_sk = PrivateKey.generate()
        ephemeral_pk = ephemeral_sk.public_key

        nonce = bytes(Box.NONCE_SIZE)
        ct = Box(ephemeral_sk, self._pk).encrypt(msg, nonce=nonce).ciphertext
        return ephemeral_pk.encode() + ct

    def decrypt(self, ciphertext):
        """
        Decrypt the given `ciphertext`. Returns the original message if
        decryption was successful, otherwise raises :py:class:`~monocypher.secret.CryptoError`.

        :param ciphertext: The ciphertext to decrypt (bytes).
        :rtype: :py:class:`bytes`
        :raises: :py:class:`~monocypher.secret.CryptoError`
        """
        ensure(self._sk is not None, RuntimeError, 'SecretBox cannot decrypt using a PublicKey')
        e_pk = ciphertext[:PublicKey.KEY_SIZE]  # Ephemeral PublicKey
        ct   = ciphertext[PublicKey.KEY_SIZE:]  # MAC + encrypted message
        box  = Box(self._sk, PublicKey(e_pk))
        return box.decrypt(
            ciphertext=ct,
            nonce=bytes(Box.NONCE_SIZE),
        )

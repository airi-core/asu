import time
import hashlib
import json
import threading
import socket
import sys
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Konfigurasi CoreSan
class Sanver:
    def __init__(self, host='localhost', port=5000):
        self.sus = []
        self.current_data = []
        self.nodes = set()
        self.host = host  # Alamat IP node ini
        self.port = port  # Port node ini
        self.sus_name = "Sanver"
        self.total_supply = "unlimited"
        self.difficulty = int(os.getenv("POW_DIFFICULTY", 2))
        self.pending_validation = []
        self.utxo_set = {}
        self.min_model_value = 1
        self.validator_reward = int(os.getenv("VALIDATOR_REWARD", 1))
        self.node_identifier = f"{self.host}:{self.port}"  # Identifikasi unik untuk node

        # Membuat blok genesis
        self.new_block(previous_hash='1', hash='1')
        self.nodes.add(self.node_identifier)  # Tambahkan node ini ke set node

        # Membuat socket server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(963369)  # Batas 5 koneksi yang diantrekan
        print(f"Sanver Node berjalan di {self.host}:{self.port}")

    def new_block(self, previous_hash, hash, transactions=None):
        """Membuat blok baru dalam CoreSan."""
        if transactions is None:
            transactions = self.current_data
        block = {
            'index': len(self.sus) + 1,
            'timestamp': time.time(),
            'data': transactions,
            'previous_hash': previous_hash,
            'hash': hash
        }
        self.current_data = []
        self.sus.append(block)
        return block

    def add_data(self, sender, data):
        """Menambahkan data baru (model AI) untuk divalidasi."""
        if not self.is_valid_address(sender):
            raise ValueError("Alamat pengirim tidak valid")
        if not self.is_valid_model_value(data):
            raise ValueError("Nilai model AI terlalu rendah")
        self.pending_validation.append({'sender': sender, 'data': data})
        return len(self.sus) + 1

    def hash(self, block):
        """Membuat hash dari sebuah blok."""
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.sus[-1]

    def proof_of_work(self, last_block, data_to_validate):
        """Proof of Work yang sekarang membutuhkan validasi data."""
        last_hash = self.hash(last_block)
        proof = 0

        while True:
            guess = f'{last_hash}{proof}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()

            if guess_hash[:self.difficulty] == '0' * self.difficulty:
                if self.validate_data(data_to_validate, proof):
                    model_value = self.calculate_model_value(data_to_validate)
                    return guess_hash, proof, model_value, self.validator_reward
            proof += 1

    def validate_data(self, data, proof):
        """Fungsi ini melakukan validasi data."""
        # Ini adalah placeholder! Ganti dengan logika validasi Anda.
        try:
            data_hash = int(hashlib.sha256(json.dumps(data).encode()).hexdigest(), 16)
            if proof == (data_hash % 1000) ** 2:
                return True
            else:
                return False
        except ValueError:
            return False

    def is_sus_valid(self, sus):
        """Memeriksa apakah rantai CoreSan yang diberikan valid."""
        previous_block = sus[0]
        block_index = 1
        utxo_set = {}

        while block_index < len(sus):
            block = sus[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                print("Previous Hash Invalid")
                return False

            # Memproses transaksi UTXO
            transactions = block['data']
            for tx in transactions:
                if 'inputs' in tx:
                    for input_tx_id, input_index in tx['inputs']:
                        if input_tx_id not in utxo_set or input_index >= len(utxo_set[input_tx_id]):
                            print("Invalid input UTXO")
                            return False
                        input_utxo = utxo_set[input_tx_id][input_index]
                        # Periksa apakah input UTXO sudah dibelanjakan
                        if input_utxo is None:
                            print("Input UTXO sudah dibelanjakan")
                            return False
                        # Hapus UTXO yang digunakan
                        utxo_set[input_tx_id][input_index] = None

                if 'outputs' in tx:
                    tx_id = self.hash(block)
                    if tx_id not in utxo_set:
                        utxo_set[tx_id] = []
                    for output in tx['outputs']:
                        utxo_set[tx_id].append(output)

            guess = f"{previous_block['hash']}{block['hash']}".encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            if guess_hash[:self.difficulty] != '0' * self.difficulty:
                print("Proof of Work Invalid")
                return False

            previous_block = block
            block_index += 1

        # Periksa apakah ada UTXO yang tidak terpakai
        for tx_id, outputs in utxo_set.items():
            for output in outputs:
                if output is not None:
                    return False  # Ada UTXO yang tidak terpakai

        return True

    def resolve_conflicts(self):
        """Fungsi konsensus."""
        neighbours = self.nodes.copy()  # Buat salinan untuk menghindari modifikasi saat iterasi
        new_sus = None
        max_length = len(self.sus)

        for node in neighbours:
            if node == self.node_identifier:
                continue  # Lewati node lokal

            try:
                other_sus = self.get_sus_from_node(node)
                if other_sus:  # Pastikan other_sus tidak None
                    length = len(other_sus)
                    if length > max_length and self.is_sus_valid(other_sus):
                        max_length = length
                        new_sus = other_sus
                else:
                    print(f"Tidak dapat mengambil rantai dari node {node}")
            except Exception as e:
                print(f"Error resolving with node {node}: {e}")

        if new_sus:
            self.sus = new_sus
            print("Rantai diganti")
            return True
        print("Rantai kita otoritatif")
        return False

    def register_node(self, address):
        """Menambahkan node baru ke jaringan."""
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def is_valid_address(self, address):
        """Memeriksa apakah alamat yang diberikan adalah alamat yang valid."""
        return isinstance(address, str) and len(address) > 10

    def is_valid_model_value(self, model_data):
        """Memeriksa apakah model AI yang diberikan memiliki nilai yang cukup untuk dianggap sebagai UTXO."""
        model_size = len(json.dumps(model_data))
        return model_size >= self.min_model_value

    def calculate_model_value(self, model_data):
        """Menghitung "nilai" dari model AI."""
        model_size = len(json.dumps(model_data))
        return model_size

    def create_transaction(self, sender, outputs):
        """Membuat transaksi baru."""
        transaction = {
            'sender': sender,
            'outputs': outputs,
        }
        return transaction

    def get_sus_from_node(self, node_address):
        """Mengambil rantai dari node lain."""
        try:
            host, port = node_address.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))
            sock.sendall(b"GET_sus")  # Kirim permintaan GET_sus
            data = sock.recv(4096)  # Terima hingga 4096 byte
            sock.close()
            if data:
                return json.loads(data.decode())
            else:
                return None
        except Exception as e:
            print(f"Error getting sus from {node_address}: {e}")
            return None

    def send_transaction(self, node_address, transaction):
        """Mengirim transaksi ke node lain."""
        try:
            host, port = node_address.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))
            sock.sendall(b"SEND_TRANSACTION:" + json.dumps(transaction).encode())
            sock.close()
        except Exception as e:
            print(f"Error sending transaction to {node_address}: {e}")

    def connect_to_node(self, node_address):
        """Menghubungkan ke node lain."""
        if node_address != self.node_identifier:  # Jangan hubungkan ke diri sendiri
            self.nodes.add(node_address)
            try:
                host, port = node_address.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))
                sock.sendall(b"REGISTER_NODE:" + f"{self.host}:{self.port}".encode())  # Kirim alamat node ini
                sock.close()
            except Exception as e:
                print(f"Gagal terhubung ke node {node_address}: {e}")

    def handle_connection(self, connection, address):
        """Menangani koneksi dari node lain."""
        try:
            while True:
                data = connection.recv(4096)
                if not data:
                    break  # Koneksi ditutup oleh pihak lain

                message = data.decode()
                if message == "GET_sus":
                    # Kirim rantai ke node yang meminta
                    connection.sendall(json.dumps(self.sus).encode())
                elif message.startswith("SEND_TRANSACTION:"):
                    try:
                        transaction_data = json.loads(message[len("SEND_TRANSACTION:") :])
                        # Tambahkan validasi transaksi di sini
                        self.current_data.append(transaction_data)
                        print(f"Menerima transaksi: {transaction_data}")
                    except json.JSONDecodeError:
                        print("Invalid transaction data")
                elif message.startswith("REGISTER_NODE:"):
                    new_node_address = message[len("REGISTER_NODE:") :]
                    self.connect_to_node(new_node_address)
                    print(f"Menerima pendaftaran node baru: {new_node_address}")
                else:
                    print(f"Menerima pesan tidak dikenal dari {address}: {message}")
        except Exception as e:
            print(f"Error handling connection from {address}: {e}")
        finally:
            connection.close()

    def start_mining(self):
        """Fungsi untuk memulai proses penambangan."""
        while True:
            if self.pending_validation:
                data_to_validate = self.pending_validation.pop(0)
                last_block = self.last_block
                hash, proof, model_value, validator_reward = self.proof_of_work(
                    last_block, data_to_validate
                )
                previous_hash = self.hash(last_block)

                # Buat transaksi untuk memasukkan model AI sebagai UTXO dan memberi reward validator
                outputs = [
                    {
                        "address": data_to_validate["sender"],
                        "value": model_value,
                        "data_hash": hashlib.sha256(
                            json.dumps(data_to_validate["data"]).encode()
                        ).hexdigest(),
                    },
                    {
                        "address": self.node_identifier,  # Kirim reward ke diri sendiri
                        "value": validator_reward,
                    },
                ]
                transaction = self.create_transaction("coinbase", outputs)
                block = self.new_block(previous_hash, hash, [transaction])
                print(f"Blok baru ditambang: {block}")

                # Sebarkan blok baru ke node lain
                self.broadcast_block(block)  # Panggil fungsi baru untuk menyebarkan blok
            else:
                time.sleep(10)

    def broadcast_block(self, block):
        """Menyebarkan blok baru ke semua node yang terhubung."""
        for node in self.nodes:
            if node != self.node_identifier:
                try:
                    host, port = node.split(":")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((host, int(port)))
                    sock.sendall(b"NEW_BLOCK:" + json.dumps(block).encode())
                    sock.close()
                except Exception as e:
                    print(f"Gagal mengirim blok ke node {node}: {e}")

    def handle_new_block(self, block):
        """Menangani blok baru yang diterima dari node lain."""
        # Tambahkan logika untuk memvalidasi blok yang masuk
        if self.is_sus_valid([self.last_block, block]):  # Periksa terhadap rantai lokal
            self.sus.append(block)
            print(f"Menerima blok baru dari node lain: {block}")
            # Setelah menerima blok baru, Anda mungkin ingin mencoba menyelesaikan konflik
            self.resolve_conflicts()

    def run(self):
        """Menjalankan node CoreSan."""
        # Mulai thread penambangan
        mining_thread = threading.Thread(target=self.start_mining)
        mining_thread.daemon = True
        mining_thread.start()

        # Terima koneksi dalam thread terpisah
        while True:
            try:
                connection, address = self.server_socket.accept()
                print(f"Menerima koneksi dari {address}")
                client_thread = threading.Thread(
                    target=self.handle_connection, args=(connection, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                print(f"Error menerima koneksi: {e}")
                break  # Keluar dari loop penerimaan jika terjadi kesalahan

if __name__ == '__main__':
    # Inisialisasi node CoreSan
    host = os.getenv('NODE_HOST', 'localhost')
    port = int(os.getenv('NODE_PORT', 5000))
    CoreSan = Sanver(host, port)

    # Hubungkan ke node lain jika ada
    other_nodes = os.getenv('OTHER_NODES')  # Contoh: "localhost:5001,localhost:5002"
    if other_nodes:
        for node_address in other_nodes.split(','):
            CoreSan.connect_to_node(node_address.strip())

    # Jalankan node
    CoreSan.run()

import hashlib

class MerkleTree:
    def __init__(self, data):
        self.data = data
        self.tree = self._build_tree(data)

    def _hash(self, data):
        # If data is bytes, hash it directly; if string, encode it first.
        if isinstance(data, bytes):
            return hashlib.sha256(data).hexdigest()
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def _build_tree(self, data):
        if not data:
            return [None]
        nodes = [self._hash(d) for d in data]
        while len(nodes) > 1:
            new_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                new_nodes.append(self._hash(left + right))
            nodes = new_nodes
        return nodes

    def get_root(self):
        return self.tree[0] if self.tree else None

    def verify_data(self, data, root):
        if not root or not self.tree:
            return False
        hashed_data = self._hash(data)
        return hashed_data in [self._hash(d) for d in self.data]

if __name__ == '__main__':
    # Example usage with binary data
    data = [b'document1', b'document2', b'document3']
    tree = MerkleTree(data)
    root = tree.get_root()
    print(f"Merkle Root: {root}")

    doc_to_verify = b'document2'
    is_valid = tree.verify_data(doc_to_verify, root)
    print(f"Verification status for {doc_to_verify}: {is_valid}")

    doc_to_verify = b'document4'
    is_valid = tree.verify_data(doc_to_verify, root)
    print(f"Verification status for {doc_to_verify}: {is_valid}")

"""
고소장 작성 다이얼로그.

기존 채팅(말풍선/사이드바)과는 완전히 별개의 화면이다 - DB에도 안 남고
RAG 검색도 안 거친다 (ComplaintController.cs 참고: LlmServer만 호출).
ViewModel.submit_complaint()/documentGenerated/complaintFailed 시그널만 사용한다.
"""
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from gui.viewmodel import ChatViewModel


class ComplaintDialog(QDialog):
    def __init__(self, viewmodel: ChatViewModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("고소장 작성")
        self.resize(560, 700)
        self.vm = viewmodel

        self._build_ui()

        # 이 다이얼로그가 열려있는 동안만 결과를 받는다 - 닫히면 연결 해제
        self.vm.documentGenerated.connect(self._on_document_generated)
        self.vm.complaintFailed.connect(self._on_complaint_failed)

    def _build_ui(self):
        self.complainant_name = QLineEdit()
        self.complainant_representative = QLineEdit()
        self.complainant_address = QLineEdit()
        self.accused_name = QLineEdit()
        self.accused_address = QLineEdit()
        self.charge = QLineEdit()
        self.incident_description = QTextEdit()
        self.incident_description.setPlaceholderText("육하원칙에 따라 사건을 설명해 주세요...")

        form = QFormLayout()
        form.addRow("고소인 명칭(회사명 또는 성명)", self.complainant_name)
        form.addRow("고소인 대표자(개인이면 비워둠)", self.complainant_representative)
        form.addRow("고소인 주소", self.complainant_address)
        form.addRow("피고소인 성명", self.accused_name)
        form.addRow("피고소인 주소", self.accused_address)
        form.addRow("죄명", self.charge)
        form.addRow("사건 설명", self.incident_description)

        self.generate_button = QPushButton("고소장 생성")
        self.generate_button.clicked.connect(self._on_generate)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#666;")

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.hide()

        self.save_button = QPushButton("다른 이름으로 저장...")
        self.save_button.clicked.connect(self._on_save)
        self.save_button.hide()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_view, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

    def _collect_fields(self) -> dict:
        return {
            "complainant_name": self.complainant_name.text().strip(),
            "complainant_representative": self.complainant_representative.text().strip(),
            "complainant_address": self.complainant_address.text().strip(),
            "accused_name": self.accused_name.text().strip(),
            "accused_address": self.accused_address.text().strip(),
            "charge": self.charge.text().strip(),
            "incident_description": self.incident_description.toPlainText().strip(),
        }

    def _on_generate(self):
        fields = self._collect_fields()

        required = [
            ("고소인 명칭", fields["complainant_name"]),
            ("고소인 주소", fields["complainant_address"]),
            ("피고소인 성명", fields["accused_name"]),
            ("피고소인 주소", fields["accused_address"]),
            ("죄명", fields["charge"]),
            ("사건 설명", fields["incident_description"]),
        ]
        missing = [label for label, value in required if not value]
        if missing:
            QMessageBox.warning(self, "입력 필요", f"다음 항목을 입력해 주세요: {', '.join(missing)}")
            return

        self.generate_button.setEnabled(False)
        self.status_label.setText("생성 중... (LLM 응답까지 시간이 걸릴 수 있습니다)")
        self.result_view.hide()
        self.save_button.hide()

        self.vm.submit_complaint(fields)

    def _on_document_generated(self, document: str):
        self.generate_button.setEnabled(True)
        self.status_label.setText("생성 완료")
        self.result_view.setPlainText(document)
        self.result_view.show()
        self.save_button.show()

    def _on_complaint_failed(self, message: str):
        self.generate_button.setEnabled(True)
        self.status_label.setText(f"[오류] {message}")

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "고소장 저장", "고소장.md", "Markdown (*.md);;모든 파일 (*)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.result_view.toPlainText())
        QMessageBox.information(self, "저장 완료", f"저장됨: {path}")

    def closeEvent(self, event):
        # 다이얼로그가 닫히면 시그널 연결 해제 - ViewModel은 창이 닫힌 뒤에도 계속 살아있으므로
        # 연결을 안 끊으면 다음에 새로 연 다이얼로그와 이중으로 연결되어 중복 반응하게 된다.
        self.vm.documentGenerated.disconnect(self._on_document_generated)
        self.vm.complaintFailed.disconnect(self._on_complaint_failed)
        super().closeEvent(event)
package com.geniuskods.identity.analysis.controller;

import com.geniuskods.identity.analysis.dto.VerifyRequest;
import com.geniuskods.identity.analysis.dto.VerifyResponse;
import com.geniuskods.identity.analysis.service.FingerprintService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/fingerprint")
@RequiredArgsConstructor
public class FingerprintController {

    private final FingerprintService fingerprintService;

    @PostMapping("/extract")
    public ResponseEntity<Map<String, String>> extract(
            @RequestParam("file") MultipartFile file)
            throws Exception {

        String template =
                fingerprintService.extractTemplate(
                        file.getBytes());

        return ResponseEntity.ok(
                Map.of("template", template)
        );
    }

    @PostMapping("/verify")
    public ResponseEntity<VerifyResponse> verify(
            @RequestBody VerifyRequest request) {

        return ResponseEntity.ok(
                fingerprintService.verify(
                        request.getProbeTemplate(),
                        request.getCandidateTemplate()
                )
        );
    }
}

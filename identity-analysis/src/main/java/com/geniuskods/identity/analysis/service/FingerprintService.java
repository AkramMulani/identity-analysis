package com.geniuskods.identity.analysis.service;

import com.geniuskods.identity.analysis.dto.VerifyResponse;
import com.machinezoo.sourceafis.FingerprintImage;
import com.machinezoo.sourceafis.FingerprintImageOptions;
import com.machinezoo.sourceafis.FingerprintMatcher;
import com.machinezoo.sourceafis.FingerprintTemplate;
import org.springframework.stereotype.Service;

import java.util.Base64;

@Service
public class FingerprintService {

    public String extractTemplate(byte[] imageBytes) {

        FingerprintImageOptions options =
                new FingerprintImageOptions()
                        .dpi(500);

        FingerprintImage image =
                new FingerprintImage(imageBytes, options);

        FingerprintTemplate template =
                new FingerprintTemplate(image);

        byte[] templateBytes =
                template.toByteArray();

        return Base64.getEncoder()
                .encodeToString(templateBytes);
    }

    public VerifyResponse verify(
            String probeTemplate,
            String candidateTemplate) {

        FingerprintTemplate probe =
                new FingerprintTemplate(
                        Base64.getDecoder()
                                .decode(probeTemplate));

        FingerprintTemplate candidate =
                new FingerprintTemplate(
                        Base64.getDecoder()
                                .decode(candidateTemplate));

        double score =
                new FingerprintMatcher(probe)
                        .match(candidate);

        boolean matched =
                score >= 40;

        return new VerifyResponse(
                score,
                matched
        );
    }
}
